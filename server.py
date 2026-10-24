import http.server
import socketserver
import json
import threading
import sqlite3
from urllib.parse import urlparse, parse_qs
from db_utils import * # Assuming db_utils.py has add_student and remove_student
import base64
import time

# Initialize the database
init_db()

# Simple in-memory store for student video frames (base64 or bytes)
# This dictionary will store the latest base64 encoded frame for each student_id
# and also their cheating flag status
student_video_frames = {}
student_states_cache = {} # Renamed from student_states to avoid conflict with db_utils

# NEW: In-memory store for student cheating status
# Format: {student_id: {'level': 'temporary_lock'/'permanently_blocked'/'normal', 'duration': float, 'timestamp': float}}
student_cheating_status = {}

# Define the database name, used in some direct queries here
DB_NAME = "quiz_app.db" # Make sure this matches db_utils.py

class QuizServerHandler(http.server.BaseHTTPRequestHandler):
    def _send_response(self, status_code, content_type, data):
        self.send_response(status_code)
        self.send_header('Content-type', content_type)
        self.send_header('Access-Control-Allow-Origin', '*') # For CORS
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def do_OPTIONS(self):
        """Handle pre-flight CORS requests."""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        data = {}
        try:
            data = json.loads(post_data.decode('utf-8'))
        except json.JSONDecodeError:
            self._send_response(400, 'application/json', {'error': 'Invalid JSON format.'})
            return

        if path == '/student/login':
            qr_code = data.get('qr_code')
            student = get_student_by_qr_code(qr_code)
            if student:
                student_id = student['student_id']
                student_name = student['name']
                # On login, assume student is 'normal' regarding cheating until detected
                student_cheating_status[student_id] = {'level': 'normal', 'duration': 0.0, 'timestamp': time.time()}
                set_student_state(student_id, can_answer=True, quiz_active=True) # Set active on login
                student_states_cache[student_id] = {'can_answer': True, 'quiz_active': True, 'name': student_name}
                self._send_response(200, 'application/json', {'status': 'success', 'student_id': student_id, 'student_name': student_name})
            else:
                self._send_response(401, 'application/json', {'status': 'error', 'message': 'Invalid QR Code'})

        elif path == '/student/submit_answer':
            student_id = data.get('student_id')
            quiz_id = data.get('quiz_id')
            question_id = data.get('question_id')
            selected_answer = data.get('selected_answer')

            if student_id is not None and quiz_id is not None and question_id is not None and selected_answer is not None:
                question = get_question_by_id(question_id)
                if question:
                    is_correct = (selected_answer == question['correct_answer'])
                    add_quiz_result(student_id, quiz_id, question_id, selected_answer, is_correct)
                    self._send_response(200, 'application/json', {'status': 'success', 'is_correct': is_correct})
                else:
                    self._send_response(404, 'application/json', {'error': 'Question not found'})
            else:
                self._send_response(400, 'application/json', {'error': 'Missing data for submission'})

        elif path == '/student/update_frame':
            student_id = data.get('student_id')
            frame_data_b64 = data.get('frame_data')
            cheating_flag = data.get('cheating_flag', False) # This flag is from old logic, new logic uses notify_cheating
            if student_id is not None and frame_data_b64:
                # Store the latest frame and cheating flag for this student
                student_video_frames[student_id] = {'frame_data': frame_data_b64, 'cheating_flag': cheating_flag}
                self._send_response(200, 'application/json', {'status': 'success'})
            else:
                self._send_response(400, 'application/json', {'error': 'Missing student_id or frame_data'})

        elif path == '/student/notify_cheating':
            student_id = data.get('student_id')
            level = data.get('level') # 'temporary_lock', 'permanently_blocked'
            duration = data.get('duration_detected')
            timestamp = data.get('timestamp')

            if student_id is not None and level and duration is not None and timestamp:
                # Update the cheating status for this student
                student_cheating_status[student_id] = {
                    'level': level,
                    'duration': duration,
                    'timestamp': timestamp
                }
                # Also, update the student's can_answer and quiz_active state if permanently blocked
                if level == 'permanently_blocked':
                    set_student_state(student_id, can_answer=0, quiz_active=0)
                    if student_id in student_states_cache:
                        student_states_cache[student_id]['can_answer'] = 0
                        student_states_cache[student_id]['quiz_active'] = 0

                self._send_response(200, 'application/json', {'status': 'success', 'message': f'Cheating notification received for student {student_id}'})
            else:
                self._send_response(400, 'application/json', {'error': 'Missing data for cheating notification'})

        elif path == '/teacher/create_quiz': # Changed from /teacher/add_quiz to match teacher.py
            title = data.get('title')
            created_by = data.get('created_by')
            questions = data.get('questions')
            if title and created_by and questions:
                quiz_id = add_quiz(title, created_by, questions)
                self._send_response(200, 'application/json', {'status': 'success', 'quiz_id': quiz_id})
            else:
                self._send_response(400, 'application/json', {'error': 'Missing quiz title, creator, or questions'})

        elif path == '/teacher/add_student':
            name = data.get('name')
            qr_code = data.get('qr_code')
            if name and qr_code:
                student_id = add_student(name, qr_code)
                self._send_response(200, 'application/json', {'status': 'success', 'message': f'Student {name} added.', 'student_id': student_id})
            else:
                self._send_response(400, 'application/json', {'error': 'Missing student name or QR code.'})

        elif path == '/teacher/remove_student': # New endpoint for removing student
            student_id = data.get('student_id')
            if student_id is not None:
                try:
                    student_id = int(student_id)
                    remove_student(student_id)
                    # Also remove from in-memory caches if they exist
                    if student_id in student_video_frames:
                        del student_video_frames[student_id]
                    if student_id in student_states_cache:
                        del student_states_cache[student_id]
                    if student_id in student_cheating_status:
                        del student_cheating_status[student_id]

                    self._send_response(200, 'application/json', {'status': 'success', 'message': f'Student ID {student_id} removed.'})
                except ValueError:
                    self._send_response(400, 'application/json', {'error': 'Invalid Student ID format.'})
                except Exception as e:
                    self._send_response(500, 'application/json', {'error': f'Failed to remove student: {e}'})
            else:
                self._send_response(400, 'application/json', {'error': 'Missing student ID.'})

        elif path == '/teacher/command':
            student_id = data.get('student_id')
            command = data.get('command')
            if student_id is not None and command:
                # Ensure student_id is an integer for consistent handling
                try:
                    student_id = int(student_id)
                except ValueError:
                    self._send_response(400, 'application/json', {'error': 'Invalid Student ID format.'})
                    return

                if command == 'disable_answering':
                    set_student_state(student_id, can_answer=0)
                    if student_id in student_states_cache:
                        student_states_cache[student_id]['can_answer'] = 0
                    self._send_response(200, 'application/json', {'status': 'success', 'message': f'Answering disabled for student {student_id}'})
                elif command == 'enable_answering':
                    set_student_state(student_id, can_answer=1)
                    if student_id in student_states_cache:
                        student_states_cache[student_id]['can_answer'] = 1
                    self._send_response(200, 'application/json', {'status': 'success', 'message': f'Answering enabled for student {student_id}'})
                elif command == 'stop_test':
                    # Set both can_answer and quiz_active to 0 to permanently stop the test
                    set_student_state(student_id, can_answer=0, quiz_active=0)
                    if student_id in student_states_cache:
                        student_states_cache[student_id]['can_answer'] = 0
                        student_states_cache[student_id]['quiz_active'] = 0
                    # If quiz is stopped, also set cheating status to normal as the test is over
                    student_cheating_status[student_id] = {'level': 'normal', 'duration': 0.0, 'timestamp': time.time()}
                    self._send_response(200, 'application/json', {'status': 'success', 'message': f'Test stopped for student {student_id}'})
                else:
                    self._send_response(400, 'application/json', {'error': 'Unknown command'})
            else:
                self._send_response(400, 'application/json', {'error': 'Missing student_id or command'})
        else:
            self._send_response(404, 'application/json', {'error': 'Not Found'})

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        query_params = parse_qs(parsed_path.query)

        if path == '/student/quiz_details':
            student_id = query_params.get('student_id', [None])[0]
            if student_id:
                student_id = int(student_id)
                student_state = get_student_state(student_id)
                quiz_active = student_state.get('quiz_active', False) if student_state else False
                can_answer = student_state.get('can_answer', False) if student_state else False

                # For simplicity, let's assume the latest quiz is the active one for now
                # In a real app, teacher would assign a quiz to students.
                latest_quiz = get_latest_quiz()
                if latest_quiz and quiz_active: # Only send quiz details if quiz is active for student
                    quiz_id = latest_quiz['quiz_id']
                    questions = get_questions_for_quiz(quiz_id)
                    # Add current question index or logic for managing quiz flow here
                    # For now, just send all questions
                    self._send_response(200, 'application/json', {
                        'status': 'success',
                        'quiz_active': quiz_active,
                        'can_answer': can_answer,
                        'quiz': latest_quiz,
                        'questions': questions
                    })
                else:
                    self._send_response(200, 'application/json', { # Send state even if no quiz active
                        'status': 'no_active_quiz',
                        'quiz_active': quiz_active,
                        'can_answer': can_answer,
                        'message': 'No active quiz or quiz stopped by teacher.'
                    })
            else:
                self._send_response(400, 'application/json', {'error': 'Student ID required.'})

        elif path == '/teacher/student_states':
            states = []
            all_students = get_all_students()
            for student in all_students:
                student_id = student['student_id']
                state = get_student_state(student_id)

                # Retrieve cheating status from in-memory cache
                cheating_info = student_cheating_status.get(student_id, {'level': 'normal', 'duration': 0.0, 'timestamp': 0.0})

                # Combine student name with their state and cheating info
                student_info = {
                    'student_id': student_id,
                    'name': student['name'],
                    'can_answer': state.get('can_answer', False) if state else False,
                    'quiz_active': state.get('quiz_active', False) if state else False,
                    'cheating_status': cheating_info['level'],
                    'cheating_duration': cheating_info['duration']
                }
                states.append(student_info)
            self._send_response(200, 'application/json', {'status': 'success', 'states': states})

        elif path == '/teacher/student_camera':
            student_id = query_params.get('student_id', [None])[0]
            if student_id:
                student_id = int(student_id)
                frame_info = student_video_frames.get(student_id)
                if frame_info:
                    self._send_response(200, 'application/json', {
                        'frame_data': frame_info['frame_data'],
                        'cheating_flag': student_cheating_status.get(student_id, {}).get('level', 'normal') != 'normal' # Use new cheating status
                    })
                else:
                    self._send_response(404, 'application/json', {'error': 'No camera feed for this student.'})
            else:
                self._send_response(400, 'application/json', {'error': 'Student ID required.'})

        elif path == '/teacher/quiz_results':
            teacher_name = query_params.get('teacher_name', [None])[0]
            if teacher_name:
                results = get_quiz_results_by_teacher(teacher_name)
                self._send_response(200, 'application/json', {'status': 'success', 'quizzes': results})
            else:
                self._send_response(400, 'application/json', {'error': 'Teacher name required.'})

        elif path == '/teacher/student_quiz_results':
            student_id_str = query_params.get('student_id', [None])[0]
            if student_id_str:
                try:
                    student_id = int(student_id_str)
                    results = get_quiz_results_by_student(student_id)
                    if results is not None:
                        self._send_response(200, 'application/json', {'status': 'success', 'results': results})
                    else:
                        self._send_response(404, 'application/json', {'error': f'Student with ID {student_id} not found or no results.'})
                except ValueError:
                    self._send_response(400, 'application/json', {'error': 'Invalid Student ID.'})
            else:
                self._send_response(400, 'application/json', {'error': 'Student ID required.'})

        else:
            self._send_response(404, 'application/json', {'error': 'Not Found'})


def run_server(port=8000):
    server_address = ('', port)
    httpd = http.server.HTTPServer(server_address, QuizServerHandler)

    print(f"Starting server on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer shutting down.")
        httpd.shutdown()
        import sys # Import sys here as it's only needed for shutdown
        sys.exit(0)

if __name__ == "__main__":
    import sys
    run_server()