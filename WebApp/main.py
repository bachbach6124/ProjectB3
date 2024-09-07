from flask import Flask, render_template, redirect, url_for, request, flash, session
import mysql.connector
import pandas as pd

app = Flask(__name__)
app.secret_key = "any-string-you-want-just-keep-it-secret"


dtb = mysql.connector.connect(
    host="127.0.0.1",  
    user="root",       
    password="super123",      
    database="gp2425" 
)


def delete(row_id):
    cursor = dtb.cursor(dictionary=True)
    
    cursor.execute("DELETE FROM classroom WHERE id = %s", (row_id,))
    dtb.commit()
    
    cursor.execute("SET @row_number = 0;")
    cursor.execute("""
        UPDATE classroom SET id = (@row_number:=@row_number + 1)
        ORDER BY id;
    """)
    
    dtb.commit()

@app.route('/', methods=['GET', 'POST'])
def homepage():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        role = request.form['choice']
        
        cursor = dtb.cursor(dictionary=True)

        
        cursor.execute("SELECT * FROM user_auth WHERE email = %s AND password = %s AND role = %s", (email, password, role))
        user = cursor.fetchone()


        if user:
            if role == 'Lecturer':
                return redirect(url_for('lecturers'))
            elif role == 'Student':
                return render_template('#')
        else:
            flash('Invalid credentials, please try again.')
            return redirect(url_for('homepage'))
    return render_template('homepage.html')
    
@app.route('/Lecturers')
def lecturers():
    return redirect(url_for('information'))

@app.route('/information', methods=['GET', 'POST'])
def information():
    if request.method == 'POST':
        row_id = request.form['row_id']
        action = request.form['action']

        if action == 'delete':
            delete(row_id)
            return redirect(url_for('information'))
        if action =='view':
            session['classroom_id'] = row_id
            return redirect(url_for('addstudent'))

    
    cursor = dtb.cursor()
    cursor.execute("SELECT * FROM classroom")
    
    classroom_data = cursor.fetchall()
    
    return render_template("/Lecturer/Information.html", classroom_data=classroom_data)


@app.route('/classroom', methods=["GET", "POST"])
def classroom():
    if request.method == 'POST':
        class_name = request.form['className']
        lecturer_name = request.form['lecturerName']
        major = request.form['major']
        start_date = request.form['startDate']
        end_date = request.form['endDate']   
        
        cursor = dtb.cursor(dictionary=True)

        cursor.execute("SELECT * FROM classroom WHERE nameofclass = %s AND major = %s", (class_name, major))
        exist_class = cursor.fetchone()
        
        if exist_class:
            flash('This class already exists !')
            return redirect('classroom')
        else:
            cursor.execute('''
                INSERT INTO classroom (nameofclass, nameoflecturer, major, begindate, enddate)
                VALUES (%s, %s, %s, %s, %s)
            ''', (class_name, lecturer_name, major, start_date, end_date))
            
            dtb.commit()
        
        cursor.execute("SET @row_number = 0;")
        cursor.execute("""
            UPDATE classroom SET id = (@row_number:=@row_number + 1)
            ORDER BY id;
        """)
    
        dtb.commit()
        return redirect(url_for('information'))       
        
    return render_template("/Lecturer/Classroom.html")

@app.route('/addstudent', methods=["GET", "POST"])
def addstudent(): 
    classroom_id = session.get('classroom_id')
    
    if request.method == "POST":
        file = request.files.get('file')

        
        if file:
            try:
                if file.filename.endswith('.csv'):
                    df = pd.read_csv(file)
                elif file.filename.endswith('.xlsx'):
                    df = pd.read_excel(file)
                else:
                    flash("Unsupported file format.", "danger")
                    return redirect(url_for('addstudent'))
                 
                cursor = dtb.cursor()
                new_students = []
                updated_classrooms = []
                for _, row in df.iterrows():
                    cursor.execute(
                        "SELECT * FROM student_information WHERE student_id = %s", (row['Student id'],)
                    )
                    existing_student = cursor.fetchone()
                    
                    if not existing_student:
                        cursor.execute(
                            "INSERT INTO student_information (student_name, student_id, major) VALUES (%s, %s, %s)",
                            (row['Student name'], row['Student id'], row['Major'])
                        )
                        new_students.append((row['Student name'], row['Student id']))
                        dtb.commit()
                        
                    cursor.execute(
                        "SELECT * FROM student_classroom WHERE student_id = %s AND classroom_id = %s",
                        (row['Student id'], classroom_id)
                    )
                    existing_classroom = cursor.fetchone()    
                        
                    if not existing_classroom:
                        cursor.execute(
                            "INSERT INTO student_classroom (student_id, classroom_id) "
                            "VALUES (%s, %s)",
                            (row['Student id'], classroom_id)
                        )
                        updated_classrooms.append((row['Student name'], row['Student id']))
                dtb.commit()
                
                if new_students:
                    for student_name, student_id in new_students:
                        flash(f'Student {student_name} (ID: {student_id}) has been inserted into the database.')
                if updated_classrooms:
                    for student_name, student_id in updated_classrooms:
                        flash(f'Student {student_name} (ID: {student_id}) has been added to classroom {classroom_id}.')
                if not new_students and not updated_classrooms:
                    flash('No new students were added or updated.')

                return redirect(url_for('addstudent'))
            

            except Exception as e:
                flash(f"An error occurred: {str(e)}", "danger")
                return redirect(url_for('addstudent'))
        else:
            flash("No file selected.", "warning")
            return redirect(url_for('addstudent'))
        
    cursor = dtb.cursor()   
    cursor.execute("""
        SELECT s.student_id, s.student_name, s.major, s.face_id
        FROM student_information s
        JOIN student_classroom sc ON s.student_id = sc.student_id
        WHERE sc.classroom_id = %s
    """, (classroom_id,))
    students = cursor.fetchall()
    
    cursor.execute("SET @row_number = 0;")
    cursor.execute("""
        UPDATE student_information SET id = (@row_number:=@row_number + 1)
        ORDER BY id;
    """)
    
    dtb.commit()
           
    return render_template("/Lecturer/AddStudent.html", students=students)

@app.route('/attendence')
def attendence():
    return render_template("/Lecturer/Attendence.html")

if __name__ == '__main__':
    app.run(debug=True)
    