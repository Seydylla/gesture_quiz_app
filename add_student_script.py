# add_student_script.py
import db_utils
import sys

def main():
    if len(sys.argv) != 3:
        print("Usage: python add_student_script.py <student_name> <qr_code>")
        sys.exit(1)

    student_name = sys.argv[1]
    qr_code = sys.argv[2]

    db_utils.init_db()
    db_utils.add_student(student_name, qr_code)
    print(f"Student '{student_name}' with QR code '{qr_code}' added (or already exists).")

if __name__ == "__main__":
    main()