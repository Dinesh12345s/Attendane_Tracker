from flask import Flask, render_template, request, redirect, session, jsonify, url_for
import mysql.connector
from datetime import datetime, date


app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database Connection
db = mysql.connector.connect(
    host="Hostname",
    user="Usernam",
    password="Password",
    database="Database name"
)
cursor = db.cursor(dictionary=True)

@app.route('/')
def home():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']

    cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s AND role=%s", (username, password, role))
    user = cursor.fetchone()

    if user:
        session['user_id'] = user['id']
        session['role'] = user['role']
        return redirect('/faculty' if role == 'faculty' else '/staff')
    else:
        return "Invalid login credentials"

@app.route('/faculty')
def faculty_dashboard():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect('/')
    faculty_id = session['user_id']
    cursor.execute("""
        SELECT DISTINCT s.id, s.roll_number, s.name AS student_name
        FROM students s
        JOIN subjects subj ON subj.faculty_id = %s
        JOIN enrollment e ON e.student_id = s.id AND e.subject_id = subj.id
    """, (faculty_id,))
    students = cursor.fetchall()

    return render_template('faculty_dashboard.html', students=students)


@app.route('/manage_subjects', methods=['GET', 'POST'])
def manage_subjects():
    if 'user_id' not in session or session.get('role') != 'faculty':
        return redirect('/')

    message = None
    faculty_id = session['user_id']

    # Fetch all staff users
    cursor.execute("SELECT id, username FROM users WHERE role = 'staff'")
    staff_members = cursor.fetchall()

    if request.method == 'POST':
        action = request.form.get('subjectAction')
        name = request.form.get('subjectName')
        code = request.form.get('subjectCode')
        staff_id = request.form.get('staff_id') or None

        if name: name = name.strip()
        if code: code = code.strip()

        if action == 'add':
            cursor.execute("SELECT * FROM subjects WHERE name=%s AND code=%s AND faculty_id=%s",
                           (name, code, faculty_id))
            if cursor.fetchone():
                message = "Subject already exists!"
            else:
                # Insert new subject
                cursor.execute("INSERT INTO subjects (name, code, faculty_id, staff_id) VALUES (%s, %s, %s, %s)",
                               (name, code, faculty_id, staff_id))
                db.commit()
                subject_id = cursor.lastrowid  # Get new subject's ID

                # Insert into staff_subject table if staff assigned
                if staff_id:
                    cursor.execute("INSERT INTO staff_subject (staff_id, subject_id) VALUES (%s, %s)",
                                   (staff_id, subject_id))
                    db.commit()

                message = "Subject added successfully!"

        elif action == 'delete':
            subject_id = request.form.get('delete_id')
            if subject_id:
                # Delete from staff_subject first to maintain referential integrity
                cursor.execute("DELETE FROM staff_subject WHERE subject_id=%s", (subject_id,))
                cursor.execute("DELETE FROM subjects WHERE id=%s AND faculty_id=%s", (subject_id, faculty_id))
                db.commit()
                message = "Subject deleted successfully!"

    # Fetch all subjects with staff username for display
    cursor.execute("""
        SELECT s.id, s.name, s.code, s.staff_id, u.username AS staff_name
        FROM subjects s
        LEFT JOIN users u ON s.staff_id = u.id
        WHERE s.faculty_id = %s
        ORDER BY s.id
    """, (faculty_id,))
    subjects = cursor.fetchall()

    return render_template("manage_subjects.html", staff_members=staff_members, subjects=subjects, message=message)

@app.route('/manage_students', methods=['GET', 'POST'])
def manage_students():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect('/')

    faculty_id = session['user_id']
    # Fetch subjects assigned to this faculty for the dropdown
    cursor.execute("SELECT id, name, code FROM subjects WHERE faculty_id = %s", (faculty_id,))
    subjects = cursor.fetchall()

    message = None

    if request.method == 'POST':
        action = request.form.get('action')
        student_name = request.form.get('studentName')
        roll_number = request.form.get('rollNumber')
        subject_ids = request.form.getlist('subjectIds')  # List of selected subjects

        if action == 'add':
            # Check if student with same roll number already exists
            cursor.execute("SELECT * FROM students WHERE roll_number = %s", (roll_number,))
            existing_student = cursor.fetchone()

            if existing_student:
                message = "Student with this roll number already exists!"
            else:
                # Add student
                cursor.execute(
                    "INSERT INTO students (name, roll_number) VALUES (%s, %s)",
                    (student_name, roll_number)
                )
                db.commit()
                student_id = cursor.lastrowid

                # Assign subjects to student (assuming enrollment table)
                for subj_id in subject_ids:
                    cursor.execute(
                        "INSERT INTO enrollment (student_id, subject_id) VALUES (%s, %s)",
                        (student_id, subj_id)
                    )
                db.commit()

                message = "Student added successfully!"

        elif action == 'delete':
            # Delete student by roll number (or you can delete by name or id, adjust as needed)
            cursor.execute("DELETE FROM students WHERE roll_number = %s", (roll_number,))
            db.commit()
            message = "Student deleted successfully!"

    return render_template('manage_students.html', subjects=subjects, message=message)


@app.route('/update_student', methods=['GET', 'POST'])
def update_student():
    if request.method == 'POST':
        student_name = request.form.get('studentName')
        roll_number = request.form.get('rollNumber')
        subject_ids = request.form.getlist('subjectIds')

        cursor.execute("SELECT id FROM students WHERE roll_number = %s AND name = %s", (roll_number, student_name))
        student = cursor.fetchone()

        if not student:
            message = "Student with provided name and roll number not found."
            return render_template('update_student.html', subjects=get_subjects(), message=message)

        student_id = student['id']
        already_enrolled = []

        for subj_id in subject_ids:
            cursor.execute(
                "SELECT * FROM enrollment WHERE student_id = %s AND subject_id = %s",
                (student_id, subj_id)
            )
            if cursor.fetchone():
                already_enrolled.append(subj_id)
            else:
                cursor.execute(
                    "INSERT INTO enrollment (student_id, subject_id) VALUES (%s, %s)",
                    (student_id, subj_id)
                )

        db.commit()

        if already_enrolled:
            format_strings = ','.join(['%s'] * len(already_enrolled))
            cursor.execute(f"SELECT name FROM subjects WHERE id IN ({format_strings})", tuple(already_enrolled))
            subject_names = [row['name'] for row in cursor.fetchall()]
            message = "Course(s) already registered: " + ", ".join(subject_names)
        else:
            message = None

        return render_template('update_student.html', subjects=get_subjects(), message=message)

    return render_template('update_student.html', subjects=get_subjects(), message=None)

def get_subjects():
    cursor.execute("SELECT id, name, code FROM subjects")
    return cursor.fetchall()

@app.route('/faculty_students')
def faculty_students():
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect('/')

    faculty_id = session['user_id']

    #  Connect using mysql.connector
    conn = mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password='Dinesh@2006',
        database='attendance_system'
    )
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT DISTINCT s.id, s.roll_number, s.name AS student_name
        FROM students s
        JOIN attendance a ON s.id = a.student_id
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE sub.faculty_id = %s
    """
    cursor.execute(query, (faculty_id,))
    students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('faculty_students.html', students=students)


@app.route('/student/<int:student_id>')
def student_report(student_id):
    if 'user_id' not in session or session['role'] != 'faculty':
        return redirect('/')

    conn = mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password='Dinesh@2006',
        database='attendance_system'
    )
    cursor = conn.cursor(dictionary=True)

    # Get student details
    cursor.execute("SELECT id, name, roll_number FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    # Get attendance stats per subject
    query = """
    SELECT 
        sub.name AS subject_name,
        sub.code AS subject_code,
        COUNT(a.id) AS present,
        (
            SELECT COUNT(DISTINCT period) 
            FROM attendance 
            WHERE subject_id = sub.id
        ) AS total_classes,
        (
            COUNT(a.id) / 
            NULLIF((
                SELECT COUNT(DISTINCT period) 
                FROM attendance 
                WHERE subject_id = sub.id
            ), 0) * 100
        ) AS percentage
    FROM subjects sub
    LEFT JOIN attendance a ON a.subject_id = sub.id 
        AND a.student_id = %s AND a.status = 1
    WHERE sub.id IN (
        SELECT subject_id 
        FROM attendance 
        WHERE student_id = %s
    )
    GROUP BY sub.id
    """
    cursor.execute(query, (student_id, student_id))  # ✅ Corrected
    report = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('individual_students.html', student=student, report=report)

@app.route('/staff')
def staff_login():
    if 'user_id' not in session or session['role'] != 'staff':
        return redirect('/')

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()

    return render_template('staff_login.html', students=students)

@app.route('/staff')
def staff_dashboard():
    if 'user_id' not in session or session['role'] != 'staff':
        return redirect('/')

    cursor.execute("SELECT * FROM students")
    students = cursor.fetchall()

    return render_template('staff_login.html', students=students)

@app.route('/take_attendance', methods=['GET', 'POST'])
def take_attendance():
    if 'user_id' not in session or session['role'] not in ['staff', 'faculty']:
        return redirect('/')

    if request.method == 'GET':
        user_role = session['role']

        if user_role == 'faculty':
            faculty_id = session['user_id']
            cursor.execute("SELECT id, name FROM subjects WHERE faculty_id = %s", (faculty_id,))
        elif user_role == 'staff':
            staff_id = session['user_id']
            cursor.execute("""
                SELECT subj.id, subj.name
                FROM subjects subj
                JOIN staff_subject ss ON ss.subject_id = subj.id
                WHERE ss.staff_id = %s
            """, (staff_id,))
        subjects = cursor.fetchall()

        selected_subject = request.args.get('subject_id', None)
        current_period = 1

        if selected_subject:
            today_str = date.today().strftime('%Y-%m-%d')
            cursor.execute("""
                SELECT MAX(period) as max_period FROM attendance
                WHERE subject_id = %s AND DATE(date_time) = %s
            """, (selected_subject, today_str))
            row = cursor.fetchone()
            if row and row['max_period']:
                current_period = row['max_period'] + 1
            else:
                current_period = 1

        return render_template('take_attendance.html', subjects=subjects,
                               selected_subject=int(selected_subject) if selected_subject else None,
                               current_period=current_period)

    # POST request for attendance scan
    try:
        data = request.get_json()
        qr_data = data.get('qr_code')
        subject_id = data.get('subject_id')
        period = data.get('period')

        if not qr_data or not subject_id or not period:
            return jsonify({'status': 'error', 'message': 'QR code, subject, or period missing'})

        cursor.execute("SELECT * FROM students WHERE student_id_barcode = %s", (qr_data,))
        student = cursor.fetchone()

        if not student:
            return jsonify({'status': 'error', 'message': 'Student not found'})

        # Check for duplicate
        cursor.execute("""
            SELECT * FROM attendance
            WHERE student_id = %s AND subject_id = %s AND period = %s AND DATE(date_time) = CURDATE()
        """, (student['id'], subject_id, period))
        if cursor.fetchone():
            return jsonify({'status': 'error', 'message': 'Duplicate scan not allowed for same period'})

        now = datetime.now()
        cursor.execute(
            "INSERT INTO attendance (student_id, subject_id, date_time, status, period) VALUES (%s, %s, %s, %s, %s)",
            (student['id'], subject_id, now, 1, period))
        db.commit()

        return jsonify({'status': 'success', 'message': f"Attendance marked for {student['name']}"})

    except Exception as e:
        print("Exception in /take_attendance:", e)
        return jsonify({'status': 'error', 'message': 'Server error occurred'})


@app.route('/close_attendance', methods=['POST'])
def close_attendance():
    try:
        subject_id = request.form.get('subject_id')
        today = date.today()

        cursor.execute("""
            SELECT MAX(period) as max_period FROM attendance
            WHERE subject_id = %s AND DATE(date_time) = %s
        """, (subject_id, today))
        row = cursor.fetchone()
        current_period = (row['max_period'] or 0)

        cursor.execute("SELECT id FROM students")
        all_students = cursor.fetchall()

        cursor.execute("""
            SELECT student_id FROM attendance
            WHERE subject_id = %s AND period = %s AND DATE(date_time) = %s
        """, (subject_id, current_period, today))
        present_ids = {row['student_id'] for row in cursor.fetchall()}

        for student in all_students:
            if student['id'] not in present_ids:
                cursor.execute(
                    "INSERT INTO attendance (student_id, subject_id, date_time, status, period) VALUES (%s, %s, NOW(), %s, %s)",
                    (student['id'], subject_id, 0, current_period))

        db.commit()

        return jsonify({'status': 'success', 'message': 'Attendance closed and absentees marked.'})

    except Exception as e:
        print("Error in /close_attendance:", e)
        return jsonify({'status': 'error', 'message': 'Failed to close attendance'})

@app.route('/view_attendance', methods=['GET'])
def view_attendance():
    if 'user_id' not in session or session.get('role') != 'staff':
        return redirect(url_for('login'))

    staff_id = session['user_id']

    db = mysql.connector.connect(
        host='127.0.0.1',
        user='root',
        password='Dinesh@2006',
        database='attendance_system'
    )
    cursor = db.cursor(dictionary=True)

    # Get staff name
    cursor.execute("SELECT username FROM users WHERE id = %s", (staff_id,))
    staff_result = cursor.fetchone()
    staff_name = staff_result['username'] if staff_result else "Unknown"

    # Get subject IDs assigned to this staff
    cursor.execute("SELECT subject_id FROM staff_subject WHERE staff_id = %s", (staff_id,))
    subject_ids = [row['subject_id'] for row in cursor.fetchall()]

    if not subject_ids:
        return render_template('view_attendance.html', staff_name=staff_name, total_periods=0, attendance_records=[])

    format_strings = ','.join(['%s'] * len(subject_ids))
    query = f"""
        SELECT a.date_time, a.subject_id, a.period,
               s.name AS student_name, s.roll_number,
               sub.name AS subject_name,
               CASE WHEN a.status = 1 THEN 'Present' ELSE 'Absent' END AS status
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        JOIN subjects sub ON a.subject_id = sub.id
        WHERE a.subject_id IN ({format_strings})
        ORDER BY a.date_time DESC, a.period ASC
    """
    cursor.execute(query, tuple(subject_ids))
    attendance_records = cursor.fetchall()

    # Format date for display and prepare set for distinct (date, period) combinations
    unique_periods = set()
    for record in attendance_records:
        date_obj = record['date_time'].date()
        record['date'] = date_obj.strftime('%Y-%m-%d')
        unique_periods.add((date_obj, record['period']))

    total_periods = len(unique_periods)

    return render_template(
        'view_attendance.html',
        staff_name=staff_name,
        total_periods=total_periods,
        attendance_records=attendance_records
    )

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':

    app.run(debug=True)
