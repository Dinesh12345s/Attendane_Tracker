

CREATE TABLE users (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(50) NOT NULL,
  password VARCHAR(100) NOT NULL,
  role ENUM('faculty','staff') NOT NULL,
  subject_id INT DEFAULT NULL,
  KEY (subject_id),
  FOREIGN KEY (subject_id) REFERENCES subjects(id)
);

CREATE TABLE students (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  roll_number VARCHAR(20) NOT NULL UNIQUE,
  name VARCHAR(100) NOT NULL,
  student_id_barcode VARCHAR(100) UNIQUE
);

CREATE TABLE subjects (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100) NOT NULL,
  code VARCHAR(20) NOT NULL,
  faculty_id INT DEFAULT NULL,
  staff_id INT DEFAULT NULL,
  KEY (faculty_id),
  KEY (staff_id),
  FOREIGN KEY (faculty_id) REFERENCES users(id),
  FOREIGN KEY (staff_id) REFERENCES users(id)
);

CREATE TABLE staff_subject (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  staff_id INT NOT NULL,
  subject_id INT NOT NULL,
  UNIQUE (staff_id, subject_id),
  KEY (subject_id),
  FOREIGN KEY (staff_id) REFERENCES users(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE enrollment (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  student_id INT DEFAULT NULL,
  subject_id INT DEFAULT NULL,
  KEY (student_id),
  KEY (subject_id),
  FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE attendance (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  student_id INT DEFAULT NULL,
  subject_id INT DEFAULT NULL,
  date_time DATETIME DEFAULT NULL,
  status TINYINT DEFAULT 1,
  period INT DEFAULT NULL,
  KEY (student_id),
  KEY (subject_id),
  FOREIGN KEY (student_id) REFERENCES students(id),
  FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);
