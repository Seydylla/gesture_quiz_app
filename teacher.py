import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, scrolledtext
import urllib.request
import urllib.parse
import json
import threading
import time

SERVER_URL = "http://192.168.1.101:8000 "

# --- Network Communication with improved error handling and non-blocking for GUI ---
def http_request_teacher(url, method='GET', params=None, data=None, headers=None, show_error_box=True):
    """
    Performs an HTTP request to the server.
    Includes comprehensive error handling for network issues, HTTP errors, and JSON parsing.
    """
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
            if 200 <= response.status < 300:
                return json.loads(response_body) if response_body else None, response.status
            else:
                error_msg = f"Serwerde näsazlyk {response.status}: {response.reason}"
                print(f"{error_msg} from {full_url}")
                if show_error_box:
                    try:
                        error_content = json.loads(response_body) if response_body else "Maglumat ýok."
                        tk.messagebox.showerror("Serwer bilen baglanmakda näsazlyk", f"{error_msg}\nMaglumatlar: {error_content}")
                    except json.JSONDecodeError:
                        tk.messagebox.showerror("Serwer bilen baglanmakda näsazlyk", f"{error_msg}\nAnyk däl jogap: {response_body}")
                return None, response.status
    except urllib.error.HTTPError as e:
        error_msg = f"HTTP baglanşykda näsazlyk {e.code}: {e.reason}"
        print(f"{error_msg} üçin {full_url}")
        if show_error_box:
            try:
                error_body = e.read().decode('utf-8')
                tk.messagebox.showerror("HTTP näsazlyk", f"{error_msg}\nSerwerden jogap: {error_body}")
                return json.loads(error_body) if error_body else None, e.code
            except Exception:
                 tk.messagebox.showerror("HTTP näsazlyk", error_msg)
        return None, e.code
    except urllib.error.URLError as e:
        error_msg = f"Torda näsazlyk: {e.reason} (Suňa baglanyp bolonok: {full_url})"
        print(error_msg)
        if show_error_box: tk.messagebox.showerror("Torda näsazlyk", error_msg)
        return None, None
    except json.JSONDecodeError as e_json:
        error_msg = f"Serwerden gereksiz jogap: {e_json}. Ulanyp bolmajak JSON."
        print(error_msg)
        return None, None
    except Exception as e_gen:
        error_msg = f"Garaşylmaýan bökdençilik: {e_gen}"
        print(f"Garaşylmaýan bökdençilik: http_request_teacher: {e_gen}")
        if show_error_box: tk.messagebox.showerror("Garaşylmaýan bökdençilik", error_msg)
        return None, None


class TeacherApp:
    """
    Main application class for the Teacher Panel.
    Manages the primary window, actions, and displays logs.
    """
    def __init__(self, master):
        self.master = master
        master.title("Mugallym Paneli")
        
        # Make the main window full screen
        try:
            master.state('zoomed') # For Windows
        except tk.TclError:
            # Fallback for other OS or if 'zoomed' fails
            master.attributes('-fullscreen', True) 

        master.minsize(900, 600) # Set a minimum size even in fullscreen (for un-fullscreening)

        # Apply a modern theme for consistent look and feel
        style = ttk.Style()
        style.theme_use('clam') # 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'

        # Configure global styles for various widgets
        style.configure('TFrame', background='#f7fafb') # Light grey background for frames
        style.configure('TLabel', font=("Arial", 11), background='#f7fafb', foreground='#20bead')
        style.configure('TButton', font=("Arial", 11, 'bold'), padding=8, background="#e7eaeb", foreground='##20bead')
        style.map('TButton', background=[('active', '#e7eaeb')]) # Darker on hover

        # Specific styles for key action buttons
        style.configure('Accent.TButton', font=('Arial', 12, 'bold'), foreground='#20bead', background='#f7fafb', padding=10)
        style.map('Accent.TButton', background=[('active', '#e7eaeb')]) # Darker blue on hover
        style.configure('Danger.TButton', font=('Arial', 12, 'bold'), foreground='#20bead', background='#f7fafb', padding=10)
        style.map('Danger.TButton', background=[('active', '#e7eaeb')]) # Darker red on hover
        style.configure('Info.TButton', font=('Arial', 12, 'bold'), foreground='#20bead', background='#f7fafb', padding=10)
        style.map('Info.TButton', background=[('active', '#e7eaeb')]) # Darker cyan on hover
        
        # Styles for labels
        style.configure('Header.TLabel', font=("Arial", 16, 'bold'), background='#f7fafb', foreground='#20bead')
        style.configure('SubHeader.TLabel', font=("Arial", 13, 'bold'), background='#f7fafb', foreground='#20bead')
        
        # Style for the scrolled text area
        style.configure('TScrolledtext', background='#f7fafb', foreground='#20bead', font=('Consolas', 10), relief='flat', borderwidth=0)


        # Main frame with grid layout for flexible resizing
        main_frame = ttk.Frame(master, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Configure grid column weights for responsive layout
        main_frame.grid_columnconfigure(0, weight=0) # Actions panel (fixed width, but can grow with content)
        main_frame.grid_columnconfigure(1, weight=1) # Info/Logs panel expands horizontally
        main_frame.grid_rowconfigure(0, weight=1) # Row expands vertically

        # Left panel for actions (Labelframe provides a nice border and title)
        actions_frame = ttk.LabelFrame(main_frame, text="Mugallymyň funksiýalary", padding="15")
        actions_frame.grid(row=0, column=0, sticky="ns", padx=10, pady=10) # Sticky "ns" makes it expand vertically

        # Action Buttons with specific styles
        ttk.Button(actions_frame, text="Täze synag", command=self.open_create_quiz_window, style='Accent.TButton').pack(pady=7, fill=tk.X)
        ttk.Button(actions_frame, text="Gatnaşyjylary sazla", command=self.open_add_remove_student_window, style='Info.TButton').pack(pady=7, fill=tk.X)
        ttk.Button(actions_frame, text="Hemme netijeleri gör", command=self.open_results_window, style='Info.TButton').pack(pady=7, fill=tk.X)
        
        # Right panel for displaying information (logs)
        info_panel = ttk.Frame(main_frame)
        info_panel.grid(row=0, column=1, sticky="nsew", padx=10, pady=10) # Sticky "nsew" makes it fill available space
        
        # Configure grid rows within info_panel for flexible resizing
        info_panel.grid_rowconfigure(0, weight=1) # Logs frame takes all vertical space
        info_panel.grid_columnconfigure(0, weight=1) # Logs frame takes all horizontal space

        # Logs Frame
        self.logs_frame = ttk.LabelFrame(info_panel, text="Programma surnallary", padding="15")
        self.logs_frame.grid(row=0, column=0, sticky="nsew", pady=5)
        self.logs_frame.grid_rowconfigure(0, weight=1) # ScrolledText expands vertically
        self.logs_frame.grid_columnconfigure(0, weight=1) # ScrolledText expands horizontally

        self.info_text = scrolledtext.ScrolledText(self.logs_frame, wrap=tk.WORD, state=tk.DISABLED, font=('Consolas', 10), height=10) # Set initial height, will expand
        self.info_text.grid(row=0, column=0, sticky="nsew")

        self.log_message("Mugallymyň paneli ýüklendi. Funksiýany saýlaň.")
        
        # Handle window closing protocol
        master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _safe_tkinter_call(self, func, *args, **kwargs):
        """
        Schedules a function call on the main Tkinter thread if the root window exists.
        This prevents errors when background threads try to update widgets after the
        main window has been closed or destroyed.
        """
        if self.master and self.master.winfo_exists():
            try:
                self.master.after(0, lambda: func(*args, **kwargs))
            except Exception as e:
                print(f"Tkinter çagyryşyny meýilleşdirmekde säwlik {func.__name__}: {e}")
                # Optional: log traceback here for debugging
                # import traceback
                # traceback.print_exc()

    def log_message(self, message):
        """
        Logs a message to the application's scrolled text log.
        Ensures thread-safe update by scheduling on the main Tkinter thread.
        """
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        full_message = f"{timestamp} {message}"
        self._safe_tkinter_call(self._update_log_gui, full_message)

    def _update_log_gui(self, message):
        """Internal method to update the log ScrolledText widget."""
        self.info_text.config(state=tk.NORMAL) # Enable writing
        self.info_text.insert(tk.END, message + "\n") # Insert new message
        self.info_text.see(tk.END) # Scroll to the end of the text
        self.info_text.config(state=tk.DISABLED) # Disable editing
        
    def open_create_quiz_window(self):
        """Opens the window for creating a new quiz."""
        self.log_message("Taze synag funksiýasy açylýar...")
        CreateQuizWindow(self.master, self)

    def open_add_remove_student_window(self):
        """Opens the window for adding or removing students."""
        self.log_message("Gatnaşyjylary sazla funksiýasy açylýar...")
        AddRemoveStudentWindow(self.master, self)

    def open_results_window(self):
        """Opens a new window to view quiz results by teacher."""
        self.log_message("Hemmeje netijeleri görkez funksiýasy açylýar...")
        ResultsWindow(self.master, self)

    def on_closing(self):
        """Handles the application closing event, prompting for confirmation."""
        if messagebox.askokcancel("Çyk", "Mugallym panelinden çykmak isleýäňizmi?"):
            self.master.destroy()
            import sys
            sys.exit() # Ensure all threads are terminated

class CreateQuizWindow(tk.Toplevel):
    """
    Toplevel window for creating a new quiz.
    Allows teacher to input quiz title, creator, and add multiple questions with answers.
    """
    def __init__(self, parent, teacher_app_ref):
        super().__init__(parent)
        self.teacher_app = teacher_app_ref # Reference to the main TeacherApp instance
        self.title("Täze synag döret")
        self.geometry("600x750") # Increased size for better form layout
        self.resizable(False, False) # Fixed size for form to maintain layout
        self.transient(parent) # Make it appear on top of the parent window
        self.grab_set() # Make modal: blocks interaction with the parent window until closed

        self.questions_data = [] # List to store questions for the current quiz draft

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Quiz Information Section
        quiz_info_frame = ttk.LabelFrame(main_frame, text="Synag maglumatlary", padding="10")
        quiz_info_frame.pack(fill=tk.X, pady=10) # Fills horizontally
        
        ttk.Label(quiz_info_frame, text="Synagyň ady:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.quiz_title_entry = ttk.Entry(quiz_info_frame, width=40)
        self.quiz_title_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW) # Expands with column
        self.quiz_title_entry.focus_set() # Set initial focus

        ttk.Label(quiz_info_frame, text="Mugallymyň ady:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.created_by_entry = ttk.Entry(quiz_info_frame, width=40)
        self.created_by_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)
        quiz_info_frame.grid_columnconfigure(1, weight=1) # Column 1 expands

        # Frame for adding questions
        questions_input_frame = ttk.LabelFrame(main_frame, text="Täze sorag goş", padding="10")
        questions_input_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(questions_input_frame, text="Sorag:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.q_text_entry = scrolledtext.ScrolledText(questions_input_frame, wrap=tk.WORD, height=3, width=40)
        self.q_text_entry.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=5)

        self.ans_entries = [] # List to hold entry widgets for answers
        for i in range(4):
            ttk.Label(questions_input_frame, text=f"Jogap {chr(ord('A')+i)}:").grid(row=i+1, column=0, sticky=tk.W, padx=5, pady=2)
            entry = ttk.Entry(questions_input_frame, width=40)
            entry.grid(row=i+1, column=1, sticky=tk.EW, padx=5, pady=2)
            self.ans_entries.append(entry)

        ttk.Label(questions_input_frame, text="Dogry jogap (A, B, C, or D):").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.correct_ans_combobox = ttk.Combobox(questions_input_frame, values=["A", "B", "C", "D"], width=5, state="readonly")
        self.correct_ans_combobox.set("A") # Default selection
        self.correct_ans_combobox.grid(row=5, column=1, sticky=tk.W, padx=5, pady=5)
        questions_input_frame.grid_columnconfigure(1, weight=1) # Column 1 expands

        ttk.Button(questions_input_frame, text="Soragy goş", command=self.add_question_to_list, style='TButton').grid(row=6, column=0, columnspan=2, pady=10)

        # Added Questions List Display (using Listbox for better overview)
        added_q_frame = ttk.LabelFrame(main_frame, text="Synagyň içindäki soraglar", padding="10")
        added_q_frame.pack(fill=tk.BOTH, expand=True, pady=10) # Fills and expands
        added_q_frame.grid_rowconfigure(0, weight=1) # Listbox row expands
        added_q_frame.grid_columnconfigure(0, weight=1) # Listbox column expands

        self.added_questions_listbox = tk.Listbox(added_q_frame, height=8, font=("Arial", 10), selectmode=tk.SINGLE)
        self.added_questions_listbox.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        list_scroll = ttk.Scrollbar(added_q_frame, orient="vertical", command=self.added_questions_listbox.yview)
        list_scroll.grid(row=0, column=1, sticky="ns")
        self.added_questions_listbox.config(yscrollcommand=list_scroll.set)

        # Button to finalize quiz creation
        ttk.Button(main_frame, text="Synagy döret", command=self.submit_quiz_threaded, style='Accent.TButton').pack(pady=15, fill=tk.X)
        
        # Handle window closing protocol for this Toplevel window
        self.protocol("WM_DELETE_WINDOW", self.close_window)
        self.update_added_questions_listbox() # Initial populate of the listbox

    def add_question_to_list(self):
        """Adds the current question data from input fields to the internal list."""
        q_text = self.q_text_entry.get("1.0", tk.END).strip()
        answers = [e.get().strip() for e in self.ans_entries]
        correct_char = self.correct_ans_combobox.get()
        
        # Validate inputs
        if not q_text:
            messagebox.showwarning("Tamamlanmadyk sorag", "Sorag doly däl.", parent=self)
            return
        if not all(answers):
            messagebox.showwarning("Tamamlanmadyk sorag", "Jogaplar doly däl.", parent=self)
            return
        if not correct_char:
            messagebox.showwarning("Tamamlanmadyk sorag", "Dogry jogaby saýlaň.", parent=self)
            return

        try:
            correct_index = ["A", "B", "C", "D"].index(correct_char)
        except ValueError:
            messagebox.showerror("Bolmojak belgi", "Dogry jogap bellenmedik.", parent=self)
            return

        self.questions_data.append({'question_text': q_text, 'answers': answers, 'correct': correct_index})
        self.update_added_questions_listbox() # Refresh the listbox display

        # Clear fields for next question input
        self.q_text_entry.delete("1.0", tk.END)
        for entry in self.ans_entries:
            entry.delete(0, tk.END)
        self.correct_ans_combobox.set("A") # Reset to default
        self.q_text_entry.focus() # Set focus for convenience
        self.teacher_app.log_message(f"Soraglar synaga goşyldy: '{q_text[:40]}...'")

    def update_added_questions_listbox(self):
        """Updates the Listbox display with currently added questions."""
        self.added_questions_listbox.delete(0, tk.END) # Clear existing items
        if not self.questions_data:
            self.added_questions_listbox.insert(tk.END, "Hiç sorag goşylmady.")
            return

        for i, q_data in enumerate(self.questions_data):
            q_display = f"Q{i+1}: {q_data['question_text'][:50]}... (Dogry: {chr(ord('A')+q_data['correct'])})"
            self.added_questions_listbox.insert(tk.END, q_display)

    def submit_quiz_threaded(self):
        """Starts a new thread to submit the quiz data to the server."""
        self.teacher_app.log_message("Synagy goşmaga synanyşmak...")
        threading.Thread(target=self.perform_submit_quiz, daemon=True).start()

    def perform_submit_quiz(self):
        """Performs the HTTP request to create the quiz on the server."""
        title = self.quiz_title_entry.get().strip()
        created_by = self.created_by_entry.get().strip()

        # Final validation before submission
        if not title or not created_by:
            self.master.after(0, lambda: messagebox.showwarning("Ýetmeýän maglumat", "Synagyň we Mugallymyň ady hökman.", parent=self))
            return
        if not self.questions_data:
            self.master.after(0, lambda: messagebox.showwarning("Sorag ýok", "Iň bolmanda 1 sorag goşmaly.", parent=self))
            return

        payload = {'title': title, 'created_by': created_by, 'questions': self.questions_data}
        response_data, status = http_request_teacher(f"{SERVER_URL}/teacher/create_quiz", method='POST', data=payload)

        if status == 200 and response_data:
            quiz_id = response_data.get('quiz_id', 'N/A')
            self.teacher_app._safe_tkinter_call(lambda: messagebox.showinfo("Success", f"Synag '{title}' ýasamak başarnykly!\nQuiz ID: {quiz_id}", parent=self))
            self.teacher_app.log_message(f"Synag '{title}' ýasaldy. ID: {quiz_id}")
            self.teacher_app._safe_tkinter_call(self.destroy) # Close window on success
        else:
            self.teacher_app.log_message(f"Synag ýasanak başarnyksyz '{title}'. Ýagdaý: {status}. Näsazlyk: {response_data.get('error', 'No error detail').strip()}")
            # http_request_teacher already shows error box, so no extra messagebox here.

    def close_window(self):
        """Closes the Create Quiz window and releases the modal lock."""
        self.teacher_app.log_message("Synag döret penjiresi ýapyldy.")
        self.destroy()
        self.grab_release() # Release modal lock

class AddRemoveStudentWindow(tk.Toplevel):
    """
    Toplevel window for managing students (add/remove).
    """
    def __init__(self, parent, teacher_app_ref):
        super().__init__(parent)
        self.teacher_app = teacher_app_ref
        self.title("Gatnaşyjylary sazla")
        self.geometry("450x350") # Fixed size for form
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Add Student Section
        add_frame = ttk.LabelFrame(main_frame, text="Täze gatnaşyjy goş", padding="10")
        add_frame.pack(fill=tk.X, padx=10, pady=10) # Fills horizontally, with external padding
        add_frame.columnconfigure(1, weight=1) # Second column expands

        ttk.Label(add_frame, text="Gatnaşyjyň ady:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.add_name_entry = ttk.Entry(add_frame, width=30)
        self.add_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.add_name_entry.focus_set()

        ttk.Label(add_frame, text="Gatnaşyjyň belgisisi:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.add_qr_entry = ttk.Entry(add_frame, width=30)
        self.add_qr_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Button(add_frame, text="Gatnaşyjyny goş", command=self.add_student_threaded, style='Accent.TButton').grid(row=2, column=0, columnspan=2, pady=10)

        # Remove Student Section
        remove_frame = ttk.LabelFrame(main_frame, text="Gatnaşyjyny aýyr", padding="10")
        remove_frame.pack(fill=tk.X, padx=10, pady=10) # Fills horizontally, with external padding
        remove_frame.columnconfigure(1, weight=1) # Second column expands

        ttk.Label(remove_frame, text="Gatnaşyjyň belgisisi:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.remove_id_entry = ttk.Entry(remove_frame, width=30)
        self.remove_id_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)

        ttk.Button(remove_frame, text="Gatnaşyjyny aýyr", command=self.remove_student_threaded, style='Danger.TButton').grid(row=1, column=0, columnspan=2, pady=10)

        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def add_student_threaded(self):
        """Initiates a threaded call to add a new student."""
        name = self.add_name_entry.get().strip()
        qr_code = self.add_qr_entry.get().strip()

        if not name or not qr_code:
            messagebox.showwarning("Maglumat gerek", "Haýyş! gatnaşyjyň adyny we belgisini giriziň", parent=self)
            return

        self.teacher_app.log_message(f"Gatnaşyjyny goşmak synanşylýar '{name}' we belgisi '{qr_code}'...")
        threading.Thread(target=self.perform_add_student, args=(name, qr_code), daemon=True).start()

    def perform_add_student(self, name, qr_code):
        """Performs the HTTP request to add a student to the server."""
        payload = {'name': name, 'qr_code': qr_code}
        response_data, status = http_request_teacher(f"{SERVER_URL}/teacher/add_student", method='POST', data=payload)

        if status == 200:
            self.teacher_app._safe_tkinter_call(lambda: messagebox.showinfo("Success", response_data.get('message', f"Gatnaşyjy '{name}' üstünlikli goşyldy."), parent=self))
            self.teacher_app.log_message(f"Gatnaşyjy '{name}' üstünlikli goşyldy. ID: {response_data.get('student_id')}")
            self.teacher_app._safe_tkinter_call(self.clear_add_fields) # Clear fields on success
        else:
            error_message = response_data.get('error', 'Unknown error.') if response_data else 'Maglumat ýok.'
            self.teacher_app._safe_tkinter_call(lambda: messagebox.showerror("Error", f"Gatnaşyjyny goşmak başarnyksyz: {error_message}", parent=self))
            self.teacher_app.log_message(f"Gatnaşyjyny goşmak başarnyksyz '{name}'. Ýagdaý: {status}. Näsazlyk: {error_message}")

    def clear_add_fields(self):
        """Clears the input fields for adding a student."""
        self.add_name_entry.delete(0, tk.END)
        self.add_qr_entry.delete(0, tk.END)

    def remove_student_threaded(self):
        """Initiates a threaded call to remove a student."""
        student_id_str = self.remove_id_entry.get().strip()
        if not student_id_str:
            messagebox.showwarning("Maglumat gerek", "Haýyş! gatnaşyjyň belgisini giriziň.", parent=self)
            return
        try:
            student_id = int(student_id_str) # Student ID is an integer
        except ValueError:
            messagebox.showerror("Maglumat gerek", "Gatnaşyjyň belgisi diňe san bolmaly.", parent=self)
            return

        # Confirmation dialog before performing sensitive action
        if not messagebox.askyesno("Aýyrmak üçin sorag", f"Hakykatdanam gatnaşyjyny aýyrjakmy: ID {student_id}?\nBu funksiýa işlemedi.", parent=self):
            self.teacher_app.log_message(f"Gatnaşyjyny aýyrmak: ID {student_id} aýryldy.")
            return

        self.teacher_app.log_message(f"Gatnaşyjyny aýyrmaga synanşylýar ID {student_id}...")
        threading.Thread(target=self.perform_remove_student, args=(student_id,), daemon=True).start()

    def perform_remove_student(self, student_id):
        """Performs the HTTP request to remove a student from the server."""
        payload = {'student_id': student_id}
        response_data, status = http_request_teacher(f"{SERVER_URL}/teacher/remove_student", method='POST', data=payload)

        if status == 200:
            self.teacher_app._safe_tkinter_call(lambda: messagebox.showinfo("Success", response_data.get('message', f"Gatnasyjy ID {student_id} başarnykly aýryldy."), parent=self))
            self.teacher_app.log_message(f"Gatnasyjy ID {student_id} başarnykly aýryldy.")
            self.teacher_app._safe_tkinter_call(lambda: self.remove_id_entry.delete(0, tk.END)) # Clear field on success
        else:
            error_message = response_data.get('error', 'Unknown error.') if response_data else 'Maglumat ýok.'
            self.teacher_app._safe_tkinter_call(lambda: messagebox.showerror("Error", f"Gatnaşyjyny aýyrmak başarnyksyz: {error_message}", parent=self))
            self.teacher_app.log_message(f"Gatnaşyjyny aýyrmak başarnyksyz ID {student_id}. Ýagdaý: {status}. Error: {error_message}")

    def close_window(self):
        """Closes the Add/Remove Student window and releases the modal lock."""
        self.teacher_app.log_message("Gatnaşyjylary sazla penjiresi ýapyldy.")
        self.destroy()
        self.grab_release()

class ResultsWindow(tk.Toplevel):
    """
    Toplevel window to display quiz results based on the teacher's name.
    """
    def __init__(self, parent, teacher_app_ref):
        super().__init__(parent)
        self.teacher_app = teacher_app_ref
        self.title("Hemmeje netijeler")
        self.geometry("900x700") # Increased size for better display of results
        self.transient(parent)
        self.grab_set()

        main_frame = ttk.Frame(self, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.grid_rowconfigure(1, weight=1) # Results text area expands
        main_frame.grid_columnconfigure(0, weight=1) # Column expands

        # Input for Teacher Name filter
        input_frame = ttk.LabelFrame(main_frame, text="Süzgüç netijeleri", padding="10")
        input_frame.grid(row=0, column=0, sticky="ew", pady=10) # Fills horizontally
        input_frame.columnconfigure(1, weight=1) # Entry field expands
        
        ttk.Label(input_frame, text="Mugallymyň ady:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.teacher_name_entry = ttk.Entry(input_frame, width=30)
        self.teacher_name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.teacher_name_entry.focus_set()
        ttk.Button(input_frame, text="Netijeleri gör", command=self.view_results_threaded, style='Info.TButton').grid(row=0, column=2, padx=10, pady=5)

        # Display area for results
        self.results_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, state=tk.DISABLED, font=('Consolas', 10))
        self.results_text.grid(row=1, column=0, sticky="nsew", padx=5, pady=5) # Fills all available space

        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def view_results_threaded(self):
        """Initiates a threaded call to fetch quiz results."""
        teacher_name = self.teacher_name_entry.get().strip()
        if not teacher_name:
            messagebox.showwarning("Maglumat gerek", "Haýyş! Mugallymyň adyny ýazyň.", parent=self)
            return

        self.teacher_app.log_message(f"Mugallym üçin synag netijelerini almak: '{teacher_name}'...")
        self._safe_results_text_update("Synag netijeleri ýüklenýär...\n", append=False) # Clear and show loading message

        threading.Thread(target=self.perform_view_results, args=(teacher_name,), daemon=True).start()

    def _safe_results_text_update(self, content, append=False):
        """
        Safely updates the results text area on the main Tkinter thread.
        `append=True` adds content, `append=False` replaces it.
        """
        if self.master and self.master.winfo_exists():
            self.master.after(0, lambda: self._update_results_text_gui(content, append))

    def _update_results_text_gui(self, content, append):
        """Internal method to update the results ScrolledText widget."""
        self.results_text.config(state=tk.NORMAL)
        if not append:
            self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, content)
        self.results_text.see(tk.END) # Scroll to the end
        self.results_text.config(state=tk.DISABLED)

    def perform_view_results(self, teacher_name):
        """Performs the HTTP request to fetch quiz results from the server."""
        params = {'teacher_name': teacher_name}
        response_data, status = http_request_teacher(f"{SERVER_URL}/teacher/quiz_results", method='GET', params=params, show_error_box=False)

        if status == 200 and response_data:
            if response_data.get('quizzes'):
                log_output = f"--- Mugallym üçin maglumatlar: '{teacher_name}' ---\n\n"
                for quiz in response_data['quizzes']:
                    log_output += f"Synag belgisi: {quiz['quiz_id']} | Title: {quiz['title']}\n"
                    if quiz['questions']:
                        for q in quiz['questions']:
                            # Corrected to display A, B, C, D for correct answer index
                            correct_answer_char = chr(ord('A') + q['correct_answer']) if isinstance(q['correct_answer'], int) else "N/A"
                            log_output += f"  Q: {q['question_text']} (Correct: {correct_answer_char})\n" 
                            if q['student_answers']:
                                for sr in q['student_answers']:
                                    # Corrected to display A, B, C, D for selected answer index
                                    selected_answer_char = chr(ord('A') + sr['selected_answer']) if isinstance(sr['selected_answer'], int) else "N/A"
                                    # FIX: Convert timestamp to float before passing to time.localtime()
                                    try:
                                        timestamp_value = float(sr.get('timestamp', time.time()))
                                    except (ValueError, TypeError):
                                        timestamp_value = time.time() # Fallback to current time if conversion fails
                                        self.teacher_app.log_message(f"Warning: Invalid timestamp format for student {sr.get('student_id')} in quiz {quiz['quiz_id']}. Using current time.")

                                    timestamp_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp_value))
                                    log_output += f"    Gatnaşyjy: {sr['student_name']} (ID: {sr['student_id']}) | Berlen: {selected_answer_char} | Dogry: {'Yes' if sr['is_correct'] else 'No'} | Wagt: {timestamp_str}\n"
                            else:
                                log_output += "    No student results for this question.\n"
                    else:
                        log_output += "  No questions for this quiz.\n"
                    log_output += "\n" # Add a newline for separation between quizzes
                log_output += "---------------------------\n"
                self._safe_results_text_update(log_output)
                self.teacher_app.log_message(f"Quiz results loaded for '{teacher_name}'.")
            else:
                self._safe_results_text_update(f"No quizzes found for teacher '{teacher_name}' or no results available.\n")
                self.teacher_app.log_message(f"No quiz results found for '{teacher_name}'.")
        else:
            self._safe_results_text_update("Failed to fetch quiz results.\n")
            self.teacher_app.log_message(f"Failed to fetch quiz results for '{teacher_name}'. Status: {status}")

    def close_window(self):
        """Closes the View Quiz Results window and releases the modal lock."""
        self.teacher_app.log_message("Hemmeje netijeler penjiresi ýapyldy.")
        self.destroy()
        self.grab_release()

def main_teacher_app():
    """Main function to initialize and run the Teacher application."""
    root = tk.Tk()
    app = TeacherApp(root)
    root.mainloop()

if __name__ == "__main__":
    main_teacher_app()