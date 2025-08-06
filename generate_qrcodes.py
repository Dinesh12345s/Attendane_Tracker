import mysql.connector
import qrcode
import os

QR_DIR = os.path.join('static', 'qrcodes')
os.makedirs(QR_DIR, exist_ok=True)

db = mysql.connector.connect(
    host="127.0.0.1",
    user="root",
    password="Dinesh@2006",
    database="attendance_system"
)
cursor = db.cursor()


cursor.execute("SELECT id, roll_number FROM students")
students = cursor.fetchall()


for student_id, roll_number in students:
    qr = qrcode.make(roll_number)
    filename = f"{roll_number}.png"
    filepath = os.path.join(QR_DIR, filename)
    qr.save(filepath)
    print(f"Generated QR for {roll_number} -> {filepath}")
    
    
    cursor.execute(
        "UPDATE students SET student_id_barcode = %s WHERE id = %s",
        (roll_number, student_id)  
    )
    db.commit()

cursor.close()
db.close()
