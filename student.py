import tkinter as tk
from tkinter import ttk, messagebox
import urllib.request
import urllib.parse
import json
import time
import threading
import sys
import cv2
import mediapipe as mp
import numpy as np
from PIL import Image, ImageTk, ImageDraw, ImageFont
import traceback
import random
import os
import subprocess

# Import the GestureDetector from gesture_utils (assuming it's in the same directory)
# from gesture_utils import GestureDetector # Make sure this file is available or provide its content if needed.

# Placeholder for GestureDetector if gesture_utils.py is not provided
# In a real scenario, you'd have this in gesture_utils.py
class GestureDetector:
    def __init__(self):
        # Initialize MediaPipe Face Detection
        self.faces = mp.solutions.face_detection.FaceDetection(
            model_selection=1, min_detection_confidence=0.0
        )
        self.last_detection_time = time.time()
        self.cheating_start_time = None
        self.cheating_duration = 0.0

    def detect(self, frame):
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_rgb.flags.writeable = False
        face_results = self.faces.process(image_rgb)
        image_rgb.flags.writeable = True

        num_faces = 0
        if face_results.detections:
            num_faces = len(face_results.detections)

        current_time = time.time()
        if num_faces > 1:
            if self.cheating_start_time is None:
                self.cheating_start_time = current_time
            self.cheating_duration = current_time - self.cheating_start_time
        else:
            self.cheating_start_time = None
            self.cheating_duration = 0.0
        
        return {
            'num_faces': num_faces,
            'cheating_duration': self.cheating_duration,
            # 'cheating_flag': num_faces > 1 # Less relevant now with duration-based locking
        }

    def close(self):
        self.faces.close()


SERVER_URL = "http://192.168.1.101:8000"

# --- Global Variables for Student App ---
student_id_global = None
student_name_global = None
root_student_window = None # To manage the main tkinter window
login_successful_flag = False # Flag to signal successful login

# --- Network Communication ---
def http_request(url, method='GET', params=None, data=None, headers=None):
    full_url = url
    if params:
        query_string = urllib.parse.urlencode(params)
        full_url = f"{url}?{query_string}"

    req_headers = {'Content-Type': 'application/json'} if data else {}
    if headers:
        req_headers.update(headers)

    req_data_bytes = json.dumps(data).encode('utf-8') if data else None

    try:
        req = urllib.request.Request(full_url, data=req_data_bytes, headers=req_headers, method=method.upper())
        with urllib.request.urlopen(req, timeout=10) as response:
            response_body = response.read().decode('utf-8')
            return json.loads(response_body) if response_body else None, response.status
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP Ýalňyşlyk {e.code}: {e.reason} {full_url} sahypadan" # Turkmen translation
        try:
            error_body = e.read().decode('utf-8')
            return json.loads(error_body) if error_body else None, e.code
        except Exception:
            return {'error': error_msg}, e.code
    except Exception as e:
        error_msg = f"Garaşylmadyk ýalňyşlyk ýüze çykdy: {e}" # Turkmen translation
        return {'error': error_msg}, None

# --- Tkinter Student Login Application ---
class StudentLoginApp:
    def __init__(self, master, on_login_success_callback):
        self.master = master
        self.on_login_success_callback = on_login_success_callback
        master.title("Gatnaşyjylaryň Girişi") # Turkmen translation
        
        # Make the login window full screen
        try:
            master.state('zoomed') # For Windows
        except tk.TclError:
            # Fallback for other OS or if 'zoomed' fails
            master.attributes('-fullscreen', True) 

        # Apply a theme
        style = ttk.Style()
        style.theme_use('clam') # 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'

        # Configure styles for login elements
        style.configure('TLabel', font=("Arial", 14))
        style.configure('TEntry', font=("Arial", 14))
        style.configure('Accent.TButton', font=('Arial', 14, 'bold'), foreground='white', background='#20bead')
        style.map('Accent.TButton', background=[('active', "#2a9e92")]) # Darker on hover

        # Create a frame to hold and center the login elements
        # Use a grid layout for centering within the frame
        self.login_frame = ttk.Frame(master, padding=(50, 50, 50, 50)) # Add significant padding
        self.login_frame.pack(expand=True, fill=tk.BOTH) # Center the frame vertically and horizontally, and make it fill

        # Configure grid within the login_frame for centering
        self.login_frame.grid_rowconfigure(0, weight=1)
        self.login_frame.grid_rowconfigure(1, weight=0) # For content
        self.login_frame.grid_rowconfigure(2, weight=0) # For content
        self.login_frame.grid_rowconfigure(3, weight=0) # For content
        self.login_frame.grid_rowconfigure(4, weight=1)

        self.login_frame.grid_columnconfigure(0, weight=1)
        self.login_frame.grid_columnconfigure(1, weight=0) # For content
        self.login_frame.grid_columnconfigure(2, weight=1)


        ttk.Label(self.login_frame, text="Gatnaşyjy belgiňizi giriziň:", font=("Arial", 16, "bold")).grid(row=1, column=1, pady=(0, 15)) # Increased font, more padding # Turkmen translation
        self.qr_entry = ttk.Entry(self.login_frame, width=35, font=("Arial", 16)) # Increased width and font
        self.qr_entry.grid(row=2, column=1, pady=15) # Increased padding
        self.qr_entry.focus()

        self.login_button = ttk.Button(self.login_frame, text="Giriş", command=self.attempt_login, style='Accent.TButton') # Turkmen translation
        self.login_button.grid(row=3, column=1, pady=20, ipadx=20, ipady=10) # Increased padding, internal padding for button size

        self.status_label = ttk.Label(self.login_frame, text="", font=("Arial", 12), foreground="#20bead")
        self.status_label.grid(row=4, column=1, pady=(10, 0), sticky='n')
        
        master.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.qr_entry.bind('<Return>', lambda event=None: self.login_button.invoke())

    def attempt_login(self):
        qr_data = self.qr_entry.get().strip() # .strip() to remove leading/trailing whitespace
        if not qr_data:
            # Removed: messagebox.showwarning("Giriş Gerek", "Gatnaşyjy belgiňizi girizi.") # Turkmen translation
            self.status_label.config(text="Gatnaşyjy belgiňizi giriziň.", foreground="red") # Display warning in status bar
            return

        self.login_button.config(state=tk.DISABLED)
        self.status_label.config(text="Giriş edilýär...", foreground="#20bead") # Turkmen translation
        
        threading.Thread(target=self.perform_login_request, args=(qr_data,), daemon=True).start()

    def perform_login_request(self, qr_data):
        global student_id_global, student_name_global, login_successful_flag
        response_data, status = http_request(f"{SERVER_URL}/student/login", method='POST', data={'qr_code': qr_data})

        if status == 200 and response_data and 'student_id' in response_data:
            student_id_global = response_data['student_id']
            student_name_global = response_data['student_name']
            self.master.after(0, lambda: self.status_label.config(text=f"Hoş geldiňiz {student_name_global}!", foreground="#20bead")) # Turkmen translation
            # Removed: messagebox.showinfo("Giriş Üstünlikli", f"Hoş geldiňiz {student_name_global}!") # Turkmen translation
            
            login_successful_flag = True # Set flag for main app logic
            self.master.after(100, self.on_login_success_callback) # Call the callback to hide login and show quiz
        else:
            error_msg = "Näbelli giriş ýalňyşlygy." # Turkmen translation
            if response_data and 'error' in response_data:
                error_msg = response_data['error']
            self.master.after(0, lambda: self.status_label.config(text=f"Giriş Şowsuz boldy: {error_msg}", foreground="red")) # Turkmen translation
            # Removed: messagebox.showerror("Giriş Şowsuz boldy", error_msg) # Turkmen translation
            self.master.after(0, lambda: self.login_button.config(state=tk.NORMAL))

    def on_closing(self):
        # Removed confirmation dialog, simply close
        self.master.destroy()
        sys.exit()

# --- NEW INTEGRATED QUIZ APPLICATION ---
class QuizApp:
    def __init__(self, root, on_back_to_login_callback):
        self.root = root
        self.on_back_to_login_callback = on_back_to_login_callback # Store the callback
        self.root.title(f"Hereketler boýunça Synag - {student_name_global}") # Turkmen translation
        # Make the quiz window full screen
        try:
            self.root.state('zoomed') # For Windows
        except tk.TclError:
            # Fallback for other OS or if 'zoomed' fails
            self.root.attributes('-fullscreen', True) 

        self.root.minsize(900, 700) # Minimum size still applies if not fullscreen or user resizes

        # Apply a modern theme for ttk widgets
        style = ttk.Style()
        style.theme_use('clam') # 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative' - 'clam' is generally more modern

        # Configure styles for various widgets
        style.configure('TLabel', font=('Arial', 12))
        style.configure('TButton', font=('Arial', 12, 'bold'))
        style.configure('Quiz.TLabel', font=('Arial', 18, 'bold'), foreground='#20bead')
        style.configure('Answer.TLabel', font=('Arial', 14), background='#f7fafb', borderwidth=1, relief="solid", padding=15)
        style.map('Answer.TLabel',
                    background=[('active', "#f7fafb"), ('selected', "#f7fafb"), ('!disabled', '#f7fafb')],
                    relief=[('selected', 'sunken'), ('!selected', 'solid')],
                    foreground=[('disabled', "#c0c0c0")]) # Text color for disabled answers
        style.configure('Status.TLabel', font=('Arial', 11, 'italic'))
        style.configure('Cheating.TLabel', font=('Arial', 12, 'bold'), foreground='#20bead')
        style.configure('Results.TLabel', font=('Arial', 16))
        style.configure('ResultTitle.TLabel', font=('Arial', 24, 'bold'), foreground='#20bead')

        # State Variables
        self.quiz_data = None
        self.current_question_index = 0
        self.selected_answer_index = None
        self.live_gesture = {"Right": "None", "Left": "None"}
        self.active_pending_action = None
        self.gesture_to_hold = None
        self.pending_timer_id = None
        self.processing_left_hand_delay = False
        self.correct_count = 0
        self.incorrect_count = 0
        self.previous_selection_history = {} # To remember selections if teacher allows navigation back
        self.quiz_active = True # Track quiz active status
        self.can_answer = True # Track if student can answer
        self.student_image = None  # To store the captured image of the student
        self.image_captured = False
        self.quiz_start_time = time.time()


        # Cheating detection variables
        self.gesture_detector = GestureDetector() # Initialize the GestureDetector
        self.lock_timer_id = None # Timer for the 30-second/2-minute lock
        self.is_quiz_locked = False # Flag to indicate if answering is locked
        self.lock_level = 'none' # 'none', '30s_lock', '2min_lock'

        # Mediapipe Setup for hands (now an instance variable)
        self.mp_hands = mp.solutions.hands
        self.mp_drawing = mp.solutions.drawing_utils
        self.hands = self.mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.6, max_num_hands=2)


        # GUI Layout
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=0) # For the back button row
        # Set column weights to 1 for exactly half and half layout
        self.root.grid_columnconfigure(0, weight=1) # Quiz area
        self.root.grid_columnconfigure(1, weight=1) # Camera area

        self.quiz_frame = ttk.Frame(root, padding="20", style='TFrame') # Add padding for a cleaner look
        self.quiz_frame.grid(row=0, column=0, sticky="nsew")
        
        self.camera_frame = ttk.Frame(root, padding="10", style='TFrame')
        self.camera_frame.grid(row=0, column=1, sticky="nsew")

        # Quiz Area Widgets
        self.question_label = ttk.Label(self.quiz_frame, text="Serwerden Synag ýüklenilýär...", wraplength=550, style='Quiz.TLabel', anchor="center") # Turkmen translation
        self.question_label.pack(pady=(25, 40), fill=tk.X) # More vertical padding

        self.answer_labels = []
        for i in range(4):
            lbl = ttk.Label(self.quiz_frame, text=f"{chr(ord('a')+i)}) ...", style='Answer.TLabel', anchor="w")
            lbl.pack(pady=10, padx=30, fill=tk.X)
            self.answer_labels.append(lbl)
        
        self.results_frame = ttk.Frame(self.quiz_frame, style='TFrame')
        # self.results_frame.pack_forget() # Initially hidden

        # Camera & Gesture Area Widgets
        self.camera_label = ttk.Label(self.camera_frame, anchor="center", relief="solid", borderwidth=1, background="#f7fafb")
        self.camera_label.pack(pady=10, padx=10, expand=True, fill=tk.BOTH)
        
        self.gesture_status_label = ttk.Label(self.camera_frame, text="Hereketler: Çep: Ýok | Sag: Ýok", font=("Arial", 14, "bold"), foreground="#20bead") # Turkmen translation
        self.gesture_status_label.pack(pady=(10, 5))
        
        self.cheating_status_label = ttk.Label(self.camera_frame, text="", style='Cheating.TLabel')
        self.cheating_status_label.pack(pady=5)

        self.status_label = ttk.Label(self.camera_frame, text="Ýagdaýy: Başlaýar...", style='Status.TLabel') # Turkmen translation
        self.status_label.pack(pady=5)
        
        # Back to Login Button - positioned below the quiz_frame, spanning both columns
        self.back_button = ttk.Button(root, text="Giriş Sahypasyna Yza", command=self.go_back_to_login, style='TButton') # Turkmen translation
        self.back_button.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")


        # Initialization
        self.stop_event = threading.Event()
        threading.Thread(target=self.fetch_quiz_data, daemon=True).start()
        self.start_camera_thread()
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _safe_tkinter_call(self, func, *args, **kwargs):
        """
        Schedules a function call on the main Tkinter thread if the root window exists.
        Uses a lambda to correctly pass args and kwargs to the target function.
        Includes a check for self.root.winfo_exists() to prevent errors after window destruction.
        """
        if self.root and self.root.winfo_exists():
            try:
                self.root.after(0, lambda: func(*args, **kwargs))
            except Exception as e:
                print(f"Tkinter jaňyny planlaşdyrmakda ýalňyşlyk {func.__name__}: {e}") # Turkmen translation
                traceback.print_exc()

    def fetch_quiz_data(self):
        last_quiz_id = None
        last_question_count = 0
        last_can_answer = False
        last_quiz_active = False

        # Initial call to display loading status
        self._safe_tkinter_call(lambda: self.question_label.config(text="Serwerden Synaga garaşylýar...")) # Turkmen translation


        while not self.stop_event.is_set():
            response_data, status = http_request(f"{SERVER_URL}/student/quiz_details", params={'student_id': student_id_global})

            if self.stop_event.is_set(): # Check again after http_request returns
                break

            if status == 200 and response_data:
                current_quiz_active = response_data.get('quiz_active', False)
                current_can_answer = response_data.get('can_answer', False)
                
                # Check for quiz stop condition
                if not current_quiz_active:
                    if last_quiz_active: # Only show message if it just changed to inactive
                        # Removed messagebox.showinfo("Synag Ýagdaýy", "Synag mugallym tarapyndan duruzuldy.") # Turkmen translation
                        self._safe_tkinter_call(self.display_quiz_stopped)
                    elif not last_quiz_active and not self.quiz_active: # Already stopped and displaying
                         pass # Do nothing, continue waiting or exiting thread
                    else: # First time detecting inactive, set the flag and update
                        self.quiz_active = False
                        self._safe_tkinter_call(self.display_quiz_stopped)
                    return # Stop polling and quiz thread

                # Update internal state variables from server response
                self.quiz_active = current_quiz_active
                self.can_answer = current_can_answer

                # Check if quiz data or question content changed
                current_quiz_id = response_data.get('quiz',{}).get('quiz_id')
                current_questions = response_data.get('questions', [])
                current_question_count = len(current_questions)

                quiz_changed = (current_quiz_id != last_quiz_id or current_question_count != last_question_count)

                if quiz_changed:
                    self.quiz_data = response_data
                    # Randomize the order of questions
                    if self.quiz_data and self.quiz_data.get('questions'):
                        random.shuffle(self.quiz_data['questions'])
                    
                    self.current_question_index = 0 # Reset to first question if quiz changes
                    self._safe_tkinter_call(self._update_quiz_display_full)
                elif current_can_answer != last_can_answer or current_quiz_active != last_quiz_active:
                    # Only update answering status visual if it changed, not the full quiz display
                    self._safe_tkinter_call(self._update_can_answer_status_visual)
                
                last_quiz_id = current_quiz_id
                last_question_count = current_question_count
                last_can_answer = current_can_answer
                last_quiz_active = current_quiz_active

            else:
                error = "Synagy ýükläp bolmady. Hiç hili işjeň Synag ýok ýa-da serwer ýalňyşlygy." # Turkmen translation
                if response_data and 'error' in response_data:
                    error = response_data['error']
                self._safe_tkinter_call(messagebox.showerror, "Synag Ýalňyşlygy", error) # Turkmen translation
                self._safe_tkinter_call(self.on_closing) # Use safe call for closing
                return # Stop polling and quiz thread

            time.sleep(2) # Poll every 2 seconds

    def _clear_quiz_display(self):
        """Helper to clear all quiz-related display elements."""
        self.question_label.config(text="")
        for lbl in self.answer_labels:
            lbl.config(text="", background=self.root.tk.call('ttk::style', 'lookup', 'Answer.TLabel', '-background'), relief="flat") # Clear text and reset appearance
            lbl.pack_forget() # Hide them
        self.results_frame.pack_forget() # Ensure results frame is hidden

    def _update_quiz_display_full(self):
        """Performs a full update of the quiz display, including resetting selection."""
        # Only deselect visually, status will be set below or by gesture
        self.deselect_answer_visual(update_status=False) 
        self.results_frame.pack_forget() # Hide results frame if it was shown

        if self.quiz_data and self.quiz_data.get('questions') and 0 <= self.current_question_index < len(self.quiz_data['questions']):
            q_data = self.quiz_data['questions'][self.current_question_index]
            self.root.title(f"Synag: {self.quiz_data.get('quiz',{}).get('title', 'Hereketler boýunça Synag')} - {student_name_global}") # Turkmen translation
            self.question_label.config(text=q_data["question_text"])
            
            for i, answer in enumerate(q_data["answers"]):
                self.answer_labels[i].config(text=f"{chr(ord('a')+i)}) {answer}", style='Answer.TLabel')
                self.answer_labels[i].pack(pady=10, padx=30, fill=tk.X) 
            self.selected_answer_index = None # Reset selected index on new question
            self._update_can_answer_status_visual() # Apply current can_answer status
        else:
            self.display_no_questions()

    def _update_can_answer_status_visual(self):
        """Updates the visual state of answer boxes and status label based on can_answer/quiz_active."""
        
        if not self.quiz_active: # If quiz is globally inactive
             self.status_label.config(text="Synag işjeň däl.", foreground="#20bead") # Turkmen translation
             for lbl in self.answer_labels:
                lbl.config(state=tk.DISABLED, background='#f7fafb', relief="flat") # Disable answers
             self.is_quiz_locked = True # Treat as locked if inactive
             return # No further updates needed
        
        if not self.can_answer or self.is_quiz_locked: # If answering is disabled or locked due to cheating
            if self.is_quiz_locked:
                if self.lock_level == '30s_lock':
                    self.status_label.config(text="Jogap bermek ýapyk: Birnäçe adam tapyldy. 30 sekunt garaşyň.", foreground="#20bead") # Turkmen translation
                elif self.lock_level == '2min_lock':
                    self.status_label.config(text="Jogap bermek ýapyk: Köp adamly tapyndy. 2 minut garaşyň.", foreground="#20bead") # Turkmen translation
                else: # Generic lock reason
                    self.status_label.config(text="Jogap bermek ýapyk: Aldawçylyk tapyldy.", foreground="#20bead") # Turkmen translation
            else: # Teacher disabled answering
                self.status_label.config(text="Jogap bermek mugallym tarapyndan wagtlaýyn ýapyldy.", foreground="#20bead") # Turkmen translation
            
            for lbl in self.answer_labels:
                lbl.config(state=tk.DISABLED, background='#f7fafb', relief="flat") # Visually disable
            
            # If an answer was selected, deselect it visually and logically if quiz becomes locked/disabled
            if self.selected_answer_index is not None and (not self.can_answer or self.is_quiz_locked):
                 self.deselect_answer_visual() # This will update status to "Selection cleared."
        else: # Quiz active and answering enabled
            # Only change status if no answer is currently selected
            if self.selected_answer_index is None:
                self.status_label.config(text="Ýagdaýy: Jogap bermäge taýyn.", foreground="#20bead") # Turkmen translation
            # else, status should reflect the selected answer.
            for lbl in self.answer_labels:
                # Reset to default ttk background for the Answer.TLabel style
                lbl.config(state=tk.NORMAL, background=self.root.tk.call('ttk::style', 'lookup', 'Answer.TLabel', '-background')) 
                lbl.config(relief="solid") # Reset relief to solid
            # Re-apply highlight if an answer is still selected (e.g., after initial load or can_answer becoming true)
            if self.selected_answer_index is not None:
                self.select_answer_visual(self.selected_answer_index, update_status=False) # Just re-apply visual, status is handled by `process_gestures` or here if no selection


    def display_no_questions(self):
        self._clear_quiz_display() # Clear current display
        self.question_label.config(text="Bu Synag üçin sorag ýok.", font=("Arial", 16, "bold"), foreground="#20bead") # Turkmen translation
        self.status_label.config(text="Synag mazmuny elýeterli däl.", foreground="#20bead") # Turkmen translation
        # Do not auto-close, allow teacher to add questions or re-enable

    def display_quiz_stopped(self):
        self._clear_quiz_display() # Clear current display
        self.question_label.config(text="Synag mugallym tarapyndan duruzuldy.", font=("Arial", 20, "bold"), foreground="#20bead") # Turkmen translation
        self.status_label.config(text="Synag işjeň däl.", foreground="#20bead") # Turkmen translation
        # Removed: messagebox.showinfo("Synag Ýagdaýy", "Synag mugallym tarapyndan duruzuldy.") # Turkmen translation
        self.root.after(100, self.on_closing) # Initiate closing the application


    def schedule_left_hand_action(self, action_type):
        # Only allow actions if quiz is active and answering is enabled AND not locked due to cheating
        if not self.quiz_active or not self.can_answer or self.is_quiz_locked:
            self._safe_tkinter_call(self.status_label.config, text="Hereket edip bolmaýar: Synag işjeň däl, jogap bermek ýapyk ýa-da ýapyk.", foreground="#20bead") # Turkmen translation
            return

        if self.processing_left_hand_delay: return
        
        # Cancel any previous timer
        if self.pending_timer_id is not None and self.root.winfo_exists():
            self.root.after_cancel(self.pending_timer_id)
            self.pending_timer_id = None

        self.processing_left_hand_delay = True
        self.active_pending_action = action_type
        self.gesture_to_hold = action_type
        delay_ms = 1000
        self._safe_tkinter_call(self.status_label.config, text=f"'{action_type.capitalize()}' tapyldy. Tassyklamak üçin {delay_ms/1000:.1f}s saklaň...") # Turkmen translation
        
        # Schedule the action on the main thread
        self.pending_timer_id = self.root.after(delay_ms, self.perform_scheduled_action)

    def perform_scheduled_action(self):
        # Only proceed if the main window still exists and the timer ID matches
        if not self.root.winfo_exists() or self.pending_timer_id is None:
            return

        self.pending_timer_id = None # Clear the timer ID immediately

        # Re-check live gesture to ensure it was held
        # REMOVED: if self.live_gesture.get("Left") != self.gesture_to_hold:
        # REMOVED:     self._safe_tkinter_call(self.status_label.config, text=f"'{self.active_pending_action}' hereketi ýatyryldy (hereket saklanmady).", foreground="#20bead") # Turkmen translation
        # REMOVED: else:
        action_to_perform = self.active_pending_action
        if action_to_perform == 'accept':
            if self.selected_answer_index is not None:
                self._safe_tkinter_call(self.status_label.config, text="Jogap iberilýär...", foreground="#20bead") # Turkmen translation
                threading.Thread(target=self.submit_answer, daemon=True).start()
            else:
                self._safe_tkinter_call(self.status_label.config, text="Kabul etmedik: Hiç hili jogap saýlanmady.", foreground="#20bead") # Turkmen translation
        elif action_to_perform == 'cancel':
            if self.selected_answer_index is not None:
                self.deselect_answer_visual() # This is handled by safe calls internally
                self.previous_selection_history[self.current_question_index] = None
                self._safe_tkinter_call(self.status_label.config, text="Saýlama ýatyryldy.", foreground="#20bead") # Turkmen translation
            elif self.current_question_index > 0:
                self.current_question_index -= 1
                self._safe_tkinter_call(self._update_quiz_display_full) # Use the full update
                self._safe_tkinter_call(self.status_label.config, text="Öňki soraga geçildi.", foreground="#20bead") # Turkmen translation
            else:
                self._safe_tkinter_call(self.status_label.config, text="Ýatyr edildi: Saýlama ýok ýa-da ilkinji sorag.", foreground="#20bead") # Turkmen translation
        
        self.processing_left_hand_delay = False
        self.active_pending_action = None
        self.gesture_to_hold = None

    def submit_answer(self):
        # Prevent submission if quiz is inactive or answering is disabled or locked
        if not self.quiz_active or not self.can_answer or self.is_quiz_locked:
            self._safe_tkinter_call(self.status_label.config, text="Iberip bolmaýar: Synag işjeň däl, jogap bermek ýapyk ýa-da ýapyk.", foreground="#20bead") # Turkmen translation
            return

        # Ensure selected_answer_index is valid before proceeding
        if self.selected_answer_index is None:
            self._safe_tkinter_call(self.status_label.config, text="Iberip bolmaýar: Hiç hili jogap saýlanmady.", foreground="#20bead") # Turkmen translation
            return

        question = self.quiz_data['questions'][self.current_question_index]
        payload = {
            'student_id': student_id_global,
            'quiz_id': self.quiz_data['quiz']['quiz_id'],
            'question_id': question['question_id'],
            'selected_answer': self.selected_answer_index
        }
        response, status = http_request(f"{SERVER_URL}/student/submit_answer", method='POST', data=payload)

        if self.stop_event.is_set(): return # Check stop event after network call

        if status == 200 and response:
            # Still track correct/incorrect answers for the final score
            if response.get('is_correct'):
                self.correct_count += 1
            else:
                self.incorrect_count += 1
            
            # Display a neutral message instead of "Correct" or "Incorrect"
            feedback_text = "Jogap kabul edildi. Indiki soraga geçilýär..." # Turkmen translation
            feedback_color = "#20bead" # Use a neutral color
            
            self._safe_tkinter_call(self.status_label.config, text=feedback_text, foreground=feedback_color)
            
            self.current_question_index += 1
            if self.current_question_index < len(self.quiz_data['questions']):
                # Shortened delay as there's no specific feedback to read
                self._safe_tkinter_call(lambda: self.root.after(1000, self._update_quiz_display_full))
            else:
                # Keep a longer delay before showing final results
                self._safe_tkinter_call(lambda: self.root.after(2000, self.calculate_and_show_results))
        else:
            error_msg = response.get('error', 'Näbelli ýalňyşlyk.') if response else 'Ulag ýalňyşlygy.' # Turkmen translation
            self._safe_tkinter_call(self.status_label.config, text=f"Ibermekde ýalňyşlyk: {error_msg}. Gaýtadan synanyşyň.", foreground="red") # Turkmen translation
            self._safe_tkinter_call(lambda: self.root.after(0, self._update_can_answer_status_visual)) # Reset status

    def calculate_and_show_results(self):
        # Only proceed if the main window still exists
        if not self.root.winfo_exists():
            return

        total = self.correct_count + self.incorrect_count
        percentage = (self.correct_count / total) * 100 if total > 0 else 0
        if percentage >= 81:   grade = "Gowy" # Turkmen translation
        elif percentage >= 61: grade = "Ortaça" # Turkmen translation
        elif percentage >= 41: grade = "Erbet" # Turkmen translation
        elif percentage >= 21: grade = "Örän erbet" # Turkmen translation
        else:                  grade = "Örän erbet" # Turkmen translation

        self.question_label.pack_forget()
        for lbl in self.answer_labels:
            lbl.pack_forget()
        
        self.results_frame.pack(pady=20, expand=True, fill=tk.BOTH)
        for widget in self.results_frame.winfo_children(): # Clear previous results if any
            widget.destroy()

        ttk.Label(self.results_frame, text="Synagyň Netijeleri", style='ResultTitle.TLabel').pack(pady=20) # Turkmen translation
        ttk.Label(self.results_frame, text=f"Jemi Soraglar: {total}", style='Results.TLabel').pack(pady=6) # Turkmen translation
        ttk.Label(self.results_frame, text=f"Dogry: {self.correct_count}", style='Results.TLabel', foreground="#20bead").pack(pady=6) # Turkmen translation
        ttk.Label(self.results_frame, text=f"Nädogry: {self.incorrect_count}", style='Results.TLabel', foreground="#20bead").pack(pady=6) # Turkmen translation
        ttk.Label(self.results_frame, text=f"Göterim: {percentage:.1f}%", style='Results.TLabel', font=("Arial", 18, "#20bead")).pack(pady=12) # Turkmen translation
        ttk.Label(self.results_frame, text=f"Baha: {grade}", style='Results.TLabel', font=("Arial", 20, "italic")).pack(pady=12) # Turkmen translation
        
        # Send final score to server
        threading.Thread(target=self.send_final_score_to_server, args=(percentage,), daemon=True).start()

        # Add the "Print Results" button
        ttk.Button(self.results_frame, text="Netijeleri Çap Et", command=self.print_results, style='TButton').pack(pady=15) # Turkmen translation

        # Add the "Close Quiz" button
        ttk.Button(self.results_frame, text="Synagy Ýap", command=self.on_closing, style='TButton').pack(pady=10) # Turkmen translation


    def send_final_score_to_server(self, percentage):
        """Sends the final quiz score to the server."""
        payload = {
            'student_id': student_id_global,
            'quiz_id': self.quiz_data['quiz']['quiz_id'] if self.quiz_data and 'quiz' in self.quiz_data else 'unknown',
            'score': percentage,
            'correct_count': self.correct_count,
            'incorrect_count': self.incorrect_count,
            'timestamp': time.time()
        }
        response, status = http_request(f"{SERVER_URL}/student/submit_score", method='POST', data=payload)
        if status != 200:
            print(f"Final netijäni ibermek şowsuz boldy: {response.get('error', 'Näbelli ýalňyşlyk')}") # Turkmen translation
        else:
            print(f"Final netije {percentage:.1f}% serwere üstünlikli iberildi.") # Turkmen translation


    def print_results(self):
        """Generates a printable image of the quiz results and sends it to the printer."""
        if not self.student_image:
            messagebox.showerror("Çap etme ýalňyşlygy", "Talyp suraty tapylmady.") # Print Error: Student image not found. # Turkmen translation
            return

        try:
            # 1. Create the printable image canvas
            WIDTH, HEIGHT = 595, 842  # A4 paper size in pixels at 72 DPI
            canvas = Image.new('RGB', (WIDTH, HEIGHT), 'white')
            draw = ImageDraw.Draw(canvas)

            # 2. Load fonts (with fallback for cross-platform compatibility)
            try:
                # Attempt to use a common system font.
                if sys.platform == "win32":
                    font_path = "arial.ttf" 
                elif sys.platform == "darwin": # macOS
                    font_path = "/System/Library/Fonts/Supplemental/Arial.ttf"
                else: # Linux, try a common font path or just assume default
                    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" # Example for Linux
                
                font_title = ImageFont.truetype(font_path, 40)
                font_body = ImageFont.truetype(font_path, 22)
                font_name = ImageFont.truetype(font_path, 28)
            except IOError:
                # Fallback to a default bitmap font if Arial is not found.
                print(f"Warning: Font {font_path} not found. Falling back to default font.") # Turkmen translation
                font_title = ImageFont.load_default()
                font_body = ImageFont.load_default()
                font_name = ImageFont.load_default()


            # 3. Add content to the canvas
            # Title
            draw.text((WIDTH / 2, 50), "Synag Netijeleri", font=font_title, fill="black", anchor="ms") # Quiz Results # Turkmen translation

            # Student Image
            # Ensure the image is not None before attempting to resize
            if self.student_image:
                photo = self.student_image.resize((180, 180))
                canvas.paste(photo, (WIDTH // 2 - 90, 100))

            # Student Name
            draw.text((WIDTH / 2, 300), student_name_global, font=font_name, fill="black", anchor="ms")

            # Results Text
            y_pos = 350
            total_questions = self.correct_count + self.incorrect_count
            percentage = (self.correct_count / total_questions) * 100 if total_questions > 0 else 0
            
            if percentage >= 81:   grade = "Gowy"
            elif percentage >= 61: grade = "Ortaça"
            elif percentage >= 41: grade = "Erbet"
            elif percentage >= 21: grade = "Örän erbet"
            else:                  grade = "Örän erbet"

            lines = [
                f"Jemi Soraglar: {total_questions}",         # Total Questions # Turkmen translation
                f"Dogry Jogaplar: {self.correct_count}",     # Correct Answers # Turkmen translation
                f"Nädogry Jogaplar: {self.incorrect_count}", # Incorrect Answers # Turkmen translation
                f"Baha: {grade} ({percentage:.1f}%)"         # Grade # Turkmen translation
            ]

            for line in lines:
                draw.text((100, y_pos), line, font=font_body, fill="black")
                y_pos += 45

            # 4. Save the canvas to a temporary file
            filepath = "quiz_results_to_print.png"
            canvas.save(filepath)

            # 5. Send the file to the default printer (OS-specific)
            if sys.platform == "win32":
                os.startfile(filepath, "print")
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["lpr", filepath], check=True)
            else:  # Linux
                subprocess.run(["lpr", filepath], check=True)
            
            messagebox.showinfo("Çap etmek", "Netijeler printere iberildi.") # Printing: Results sent to printer. # Turkmen translation

        except FileNotFoundError:
            # This can happen if 'lpr' is not installed on Linux/macOS
            messagebox.showerror("Çap etme ýalňyşlygy", "Çap ediş buýrugy tapylmady. 'lpr' gurnalanmy?") # Print Error: Print command not found. Is 'lpr' installed? # Turkmen translation
        except Exception as e:
            messagebox.showerror("Çap etme ýalňyşlygy", f"Garaşylmadyk ýalňyşlyk ýüze çykdy: {e}") # Print Error: An unexpected error occurred. # Turkmen translation

    def process_gestures(self, frame):
        # Draw MediaPipe hands landmarks for visual feedback
        image_for_display = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_for_display.flags.writeable = False
        
        # Use the gesture_detector for cheating detection
        detection_results = self.gesture_detector.detect(image_for_display)
        cheating_duration = detection_results['cheating_duration']
        num_faces = detection_results['num_faces']

        # Update cheating status label
        if num_faces > 1:
            self._safe_tkinter_call(self.cheating_status_label.config, text=f"Birnäçe adam tapyldy! {cheating_duration:.1f}s aldawçylyk edilýär", foreground="#20bead") # Turkmen translation
        else:
            self._safe_tkinter_call(self.cheating_status_label.config, text="", foreground="#20bead") # Clear message

        # Cheating logic based on duration
        if num_faces > 1:
            if self.lock_level == 'none': # If no lock is active yet
                if 5 <= cheating_duration < 10:
                    self.is_quiz_locked = True
                    self.lock_level = '30s_lock'
                    self._safe_tkinter_call(self._update_can_answer_status_visual)
                    # Cancel any existing timer to avoid conflicts
                    if self.lock_timer_id is not None and self.root.winfo_exists():
                        self.root.after_cancel(self.lock_timer_id)
                    self.lock_timer_id = self.root.after(30000, self.release_quiz_lock)
                    threading.Thread(target=self.send_cheating_notification, args=("temporary_lock_30s", cheating_duration), daemon=True).start()
                elif cheating_duration >= 10 and self.lock_level != '2min_lock': # Ensure not already 2min lock
                    self.is_quiz_locked = True
                    self.lock_level = '2min_lock'
                    self._safe_tkinter_call(self._update_can_answer_status_visual)
                    if self.lock_timer_id is not None and self.root.winfo_exists():
                        self.root.after_cancel(self.lock_timer_id)
                    self.lock_timer_id = self.root.after(120000, self.release_quiz_lock) # 2 minutes = 120000 ms
                    threading.Thread(target=self.send_cheating_notification, args=("temporary_lock_2min", cheating_duration), daemon=True).start()
        elif num_faces <= 1 and self.is_quiz_locked and self.lock_timer_id is not None:
            # If cheating stops, but a lock is active, the timer will continue to release it.
            # No action needed here, the timer will expire and release the lock.
            pass
        elif num_faces <= 1 and self.is_quiz_locked and self.lock_timer_id is None:
            # This case means the lock timer has already expired or was manually cleared.
            # We should reset lock state if it was somehow stuck.
            self.is_quiz_locked = False
            self.lock_level = 'none'
            self._safe_tkinter_call(self._update_can_answer_status_visual)


        # --- Hand gesture processing for answers (independent of cheating) ---
        # Ensure MediaPipe hands is still active before processing
        hands_results = None
        if hasattr(self, 'hands') and self.hands is not None: # Use self.hands
            try:
                hands_results = self.hands.process(image_for_display) # Use self.hands
            except Exception as e:
                print(f"Elleri işlemekde ýalňyşlyk: {e}") # Turkmen translation
                hands_results = None
        
        image_for_display.flags.writeable = True # Re-enable writeability for drawing

        # Removed: mp_drawing.draw_landmarks(image_for_display, hand_landmarks, mp_hands.HAND_CONNECTIONS)
        # Hand points will no longer be drawn.
        # Use self.hands.process here as well
        results = self.hands.process(image_for_display)

        current_frame_gestures = {"Right": "None", "Left": "None"}
        if results.multi_hand_landmarks and results.multi_handedness:
            processed_hands_count = len(results.multi_hand_landmarks)
            # Ensure handedness info matches landmarks count
            if len(results.multi_handedness) != processed_hands_count:
                 print("Warning: Mismatch between landmarks and handedness count.")
                 # Skip processing this frame if counts don't match to avoid errors
                 return image_for_display # Return original image

            for i, hand_landmarks in enumerate(results.multi_hand_landmarks):
                # Determine Handedness ("Left" or "Right")
                handedness_info = results.multi_handedness[i]
                hand_label = handedness_info.classification[0].label

                # --- Basic Gesture Recognition Logic ---
                gesture = "None" # Default for this hand in this frame
                try:
                    landmarks = hand_landmarks.landmark
                    # Get key landmark coordinates
                    thumb_tip = landmarks[self.mp_hands.HandLandmark.THUMB_TIP]
                    thumb_ip = landmarks[self.mp_hands.HandLandmark.THUMB_IP]
                    index_tip = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_TIP]
                    index_pip = landmarks[self.mp_hands.HandLandmark.INDEX_FINGER_PIP]
                    middle_tip = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_TIP]
                    middle_pip = landmarks[self.mp_hands.HandLandmark.MIDDLE_FINGER_PIP]
                    ring_tip = landmarks[self.mp_hands.HandLandmark.RING_FINGER_TIP]
                    ring_pip = landmarks[self.mp_hands.HandLandmark.RING_FINGER_PIP]
                    pinky_tip = landmarks[self.mp_hands.HandLandmark.PINKY_TIP]
                    pinky_pip = landmarks[self.mp_hands.HandLandmark.PINKY_PIP]

                    # Function to check if finger is extended (tip vertically higher than pip)
                    def is_finger_up(tip, pip, threshold=0.02):
                        # Add a small threshold to avoid noise
                        return tip.y < pip.y - threshold

                    # Check which fingers are up
                    fingers_up = [
                        is_finger_up(index_tip, index_pip),
                        is_finger_up(middle_tip, middle_pip),
                        is_finger_up(ring_tip, ring_pip),
                        is_finger_up(pinky_tip, pinky_pip)
                    ]
                    num_fingers_up = sum(fingers_up)

                    # Thumb status (tip vertically higher than intermediate joint)
                    is_thumb_up = is_finger_up(thumb_tip, thumb_ip, threshold=0.03)

                    # Fist check (all non-thumb fingers are curled down)
                    is_fist = not any(fingers_up) # Simplified: no fingers extended

                    # --- Assign gesture based on hand label and finger states ---
                    if hand_label == "Right":
                        if num_fingers_up == 1 and fingers_up[0]: gesture = '1'
                        elif num_fingers_up == 2 and fingers_up[0] and fingers_up[1]: gesture = '2'
                        elif num_fingers_up == 3 and fingers_up[0] and fingers_up[1] and fingers_up[2]: gesture = '3'
                        elif num_fingers_up == 4 and all(fingers_up): gesture = '4'
                        # Add other right-hand gestures if needed
                    elif hand_label == "Left":
                        if is_thumb_up and num_fingers_up == 0: gesture = 'accept'
                        elif num_fingers_up == 4 and all(fingers_up): gesture = 'cancel'
                        # Add other left-hand gestures if needed

                    # Store the detected gesture for this hand in this frame
                    current_frame_gestures[hand_label] = gesture

                except Exception as e:
                    print(f"Üsti bellikleri gaýtadan işlemekde säwlik {hand_label} eli: {e}")
                    current_frame_gestures[hand_label] = "Ýalňyşlyk" # Mark as error

                # --- Trigger Actions based on NEW Gestures ---
                # Check if the gesture is significant (not None/Error) and DIFFERENT from the last known state for this hand
                if gesture not in ["None", "Error"] and gesture != self.live_gesture.get(hand_label):

                    if hand_label == "Right" and gesture in ['1', '2', '3', '4']:
                        # Right hand answers - act immediately IF no left hand action is pending
                        if not self.processing_left_hand_delay:
                             answer_index = int(gesture) - 1
                             # Schedule GUI update in main thread
                             self.root.after(0, self.select_answer_visual, answer_index)
                        else:
                             # Indicate that right hand is blocked by left hand delay
                             self.root.after(0, lambda: self.status_label.config(text="Sag eliň herektine garaşylýar...")) # Turkmen translation

                    elif hand_label == "Left" and gesture in ['accept', 'cancel']:
                        # Left hand actions - schedule the delay check
                        self.root.after(0, self.schedule_left_hand_action, gesture) # Turkmen translation

        self.live_gesture = current_frame_gestures
        status_text = f"Hereketler: Çep: {self.live_gesture['Right']} | Sag: {self.live_gesture['Left']}" # Turkmen translation
        self._safe_tkinter_call(self.gesture_status_label.config, text=status_text)
        return image_for_display

    def release_quiz_lock(self):
        """Releases the temporary quiz lock."""
        self.is_quiz_locked = False
        self.lock_level = 'none'
        self.lock_timer_id = None
        self._safe_tkinter_call(self._update_can_answer_status_visual)
        self._safe_tkinter_call(self.status_label.config, text="Synaga jogap bermek açyldy. Dowam edip bilersiňiz.", foreground="#20bead") # Turkmen translation

    def send_cheating_notification(self, level, duration):
        """Sends a cheating notification to the server."""
        payload = {
            'student_id': student_id_global,
            'quiz_id': self.quiz_data['quiz']['quiz_id'] if self.quiz_data and 'quiz' in self.quiz_data else 'unknown',
            'notification_type': 'cheating_detected',
            'level': level, # 'temporary_lock_30s' or 'temporary_lock_2min'
            'duration_detected': duration,
            'timestamp': time.time()
        }
        response, status = http_request(f"{SERVER_URL}/student/notify_cheating", method='POST', data=payload)
        if status != 200:
            print(f"Aldawçylyk bildirişini ibermek şowsuz boldy: {response.get('error', 'Näbelli ýalňyşlyk')}") # Turkmen translation

    def camera_loop(self):
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            self._safe_tkinter_call(messagebox.showerror, "Kamera Ýalňyşlygy", "Web-kamera açylyp bilmedi.") # Turkmen translation
            self.stop_event.set() # Set stop event to terminate thread
            return

        try:
            while not self.stop_event.is_set():
                ret, frame = cap.read()
                if not ret:
                    print("Kadry alyp bilmedi, kamera aýryldy ýa-da eýýäm ulanylýar.") # Turkmen translation
                    # Removed messagebox.showerror for camera error
                    self.stop_event.set() # Set stop event to terminate thread
                    break
                
                # Capture student image once, 3 seconds after quiz starts
                if not self.image_captured and (time.time() - self.quiz_start_time) > 3:
                    if frame is not None:
                        # Convert from BGR (OpenCV) to RGB (PIL) before storing
                        self.student_image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        self.image_captured = True
                        
                        # Briefly notify the user that a photo was taken
                        self._safe_tkinter_call(self.status_label.config, text="Surat düşürildi!", foreground="#20bead") # Photo taken! # Turkmen translation
                        
                        # Define a function to reset the status label to its normal state
                        def reset_status_after_photo():
                            if not self.root.winfo_exists(): return
                            if self.selected_answer_index is None:
                                self._safe_tkinter_call(self.status_label.config, text="Ýagdaýy: Jogap bermäge taýyn.", foreground="#20bead") # Turkmen translation
                            else:
                                self._safe_tkinter_call(self.status_label.config, text=f"'{chr(ord('a') + self.selected_answer_index)}' jogaby saýlandy.", foreground="#20bead") # Turkmen translation
                        
                        if self.root.winfo_exists():
                            self.root.after(2500, reset_status_after_photo)
                
                frame = cv2.flip(frame, 1) # Mirror image for display

                # Check stop_event again immediately before processing gestures
                if self.stop_event.is_set():
                    break
                
                processed_frame_rgb = self.process_gestures(frame)
                
                img = Image.fromarray(processed_frame_rgb)
                
                # Use fixed dimensions as requested by the user
                new_width = 640
                new_height = 480
                
                if new_width > 0 and new_height > 0:
                    img_resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                    imgtk = ImageTk.PhotoImage(image=img_resized)
                    self._safe_tkinter_call(self._update_camera_label_gui, imgtk)
                
                time.sleep(0.03) # Roughly 30 fps
        finally:
            cap.release()
            print("Kamera goýberildi.") # Turkmen translation
            # Ensure self.hands.close() and face_detection.close() are called
            if self.hands: # Use self.hands
                try:
                    self.hands.close() # Use self.hands.close()
                    print("Mediapipe elleri ýapyldy.") # Turkmen translation
                except Exception as e:
                    print(f"Mediapipe ellerini ýapmakda ýalňyşlyk: {e}") # Turkmen translation
                self.hands = None # Dereference to ensure it's truly closed
            
            # Close GestureDetector's resources as well
            if self.gesture_detector:
                try:
                    self.gesture_detector.close() # Now GestureDetector has a close method
                    print("GestureDetector serişdeleri ýapyldy.") # Turkmen translation
                except Exception as e:
                    print(f"GestureDetector serişdelerini ýapmakda ýalňyşlyk: {e}") # Turkmen translation


    def start_camera_thread(self):
        # self.hands is now initialized in QuizApp's __init__
        threading.Thread(target=self.camera_loop, daemon=True).start()

    def _update_camera_label_gui(self, imgtk):
        # This method is designed to be called safely on the main thread via _safe_tkinter_call
        if self.root.winfo_exists():
            self.camera_label.imgtk = imgtk
            self.camera_label.config(image=imgtk)

    def select_answer_visual(self, index, update_status=True):
        # This method is designed to be called safely on the main thread via _safe_tkinter_call
        if not (0 <= index < len(self.answer_labels)): return

        # Only proceed if answering is allowed
        if not self.quiz_active or not self.can_answer or self.is_quiz_locked:
            return

        # Deselect previous answer visually
        if self.selected_answer_index is not None and self.selected_answer_index != index:
             # Use ttk::style lookup for the default background color
             self.answer_labels[self.selected_answer_index].config(
                 background=self.root.tk.call('ttk::style', 'lookup', 'Answer.TLabel', '-background'), 
                 relief="solid"
             )

        self.answer_labels[index].config(background="#A0A0A0", relief="sunken")
        self.selected_answer_index = index
        if update_status: self.status_label.config(text=f"'{chr(ord('a') + index)}' jogaby saýlandy.", foreground="#20bead") # Turkmen translation

    def deselect_answer_visual(self, update_status=True):
        # This method is designed to be called safely on the main thread via _safe_tkinter_call
         if self.selected_answer_index is not None:
             # Use ttk::style lookup for the default background color
             self.answer_labels[self.selected_answer_index].config(
                 background=self.root.tk.call('ttk::style', 'lookup', 'Answer.TLabel', '-background'), 
                 relief="solid"
             )
             self.selected_answer_index = None
             if update_status: self.status_label.config(text="Saýlama ýatyryldy.", foreground="#20bead") # Turkmen translation
         else:
             if update_status: self.status_label.config(text="Ýatyrmak üçin saýlama ýok.", foreground="#20bead") # Turkmen translation

    def go_back_to_login(self):
        # Removed confirmation dialog, simply hide quiz and show login
        self.stop_event.set() # Stop camera and quiz threads
        # Give a moment for the camera thread to clean up
        time.sleep(0.5)
        if self.root and self.root.winfo_exists():
            self.root.withdraw() # Hide the quiz window
        # Call the callback to show the login window
        self.on_back_to_login_callback()


    def on_closing(self):
        # Removed confirmation dialog, simply close
        self.stop_event.set() # Signal the camera loop to stop
        # Give a moment for the camera thread to clean up
        time.sleep(0.5) 
        # Also close Mediapipe resources specifically when the QuizApp closes
        if self.hands:
            try:
                self.hands.close()
                print("Mediapipe elleri ýapyldy on_closing.")
            except Exception as e:
                print(f"Error closing Mediapipe hands in on_closing: {e}")
            self.hands = None # Ensure it's dereferenced
        
        if self.gesture_detector:
            try:
                self.gesture_detector.close()
                print("GestureDetector serişdeleri ýapyldy on_closing.")
            except Exception as e:
                print(f"Error closing GestureDetector in on_closing: {e}")

        if self.root and self.root.winfo_exists():
            self.root.destroy()
        sys.exit()

# --- Main Application Runner ---
class MainStudentApp:
    def __init__(self):
        self.login_window = tk.Tk()
        self.login_app = StudentLoginApp(self.login_window, self.show_quiz_window)
        
        self.quiz_window = None # Will be created when login is successful

    def show_quiz_window(self):
        self.login_window.withdraw() # Hide the login window
        if self.quiz_window is None:
            self.quiz_window = tk.Toplevel(self.login_window) # Create as a Toplevel of the hidden login window
            self.quiz_app = QuizApp(self.quiz_window, self.show_login_window)
        else:
            # If the quiz_window already exists but was withdrawn (e.g., came back from login),
            # ensure its resources are re-initialized or confirmed to be ready.
            # In this specific case, QuizApp's __init__ will re-initialize self.hands etc.
            # so we just need to deiconify.
            self.quiz_window.deiconify() # Show the quiz window if it already exists

    def show_login_window(self):
        if self.quiz_app:
            self.quiz_app.stop_event.set() # Stop any running threads in QuizApp
            self.quiz_app.root.destroy() # Destroy the quiz window and its components
            self.quiz_window = None # Reset the quiz window reference
            self.quiz_app = None # Explicitly dereference the quiz_app instance

        global student_id_global, student_name_global, login_successful_flag
        student_id_global = None
        student_name_global = None
        login_successful_flag = False

        # Clear the QR entry and enable the login button for a new login attempt
        self.login_app.qr_entry.delete(0, tk.END)
        self.login_app.login_button.config(state=tk.NORMAL)
        self.login_app.status_label.config(text="")
        
        self.login_window.deiconify() # Show the login window

        # Re-apply fullscreen attributes when showing the login window again
        try:
            self.login_window.state('zoomed') # For Windows
        except tk.TclError:
            self.login_window.attributes('-fullscreen', True)

    def run(self):
        self.login_window.mainloop()
        
        # If the login window was closed (e.g., via on_closing), ensure quiz_window is also destroyed if it exists.
        # This part will be reached if mainloop exits, for example, if the user closes the login window
        if self.quiz_window and self.quiz_window.winfo_exists():
            self.quiz_window.destroy()

if __name__ == "__main__":
    app = MainStudentApp()
    app.run()