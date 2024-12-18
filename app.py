import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def connect_db():
    conn = psycopg2.connect(
        dbname=st.secrets["database"]["DB_NAME"],
        user=st.secrets["database"]["DB_USER"],
        password=st.secrets["database"]["DB_PASSWORD"],
        host=st.secrets["database"]["DB_HOST"],
        port=st.secrets["database"]["DB_PORT"]
    )
    return conn

def get_employees():
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT fullname, phone, email 
        FROM employee 
        WHERE id IN (373, 379, 403, 398, 395, 399, 356, 406, 390, 378, 5, 402, 401, 405, 391)
    """)
    employees = cursor.fetchall()
    conn.close()
    return employees

def insert_attendance(fullname, phone, email, status, date_time, meeting_time):
    conn = connect_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO employee_attendance (fullname, phone, email, employee_status, date_time, meeting_time)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (fullname, phone, email, status, date_time, meeting_time))
    conn.commit()
    conn.close()

st.title("Employee Attendance")

meeting_time = st.selectbox("Select meeting time:", ["11 AM", "4 PM"])
employees = get_employees()

current_time = datetime.now()
time_limit_11am = datetime.combine(datetime.today(), datetime.strptime("11:00", "%H:%M").time()) + timedelta(hours=1)
time_limit_4pm = datetime.combine(datetime.today(), datetime.strptime("16:00", "%H:%M").time()) + timedelta(hours=1)

if meeting_time == "11 AM" and current_time > time_limit_11am:
    st.warning("Time limit exceeded. You can only select a time until 12:00 PM for 11 AM meeting.")
elif meeting_time == "4 PM" and current_time > time_limit_4pm:
    st.warning("Time limit exceeded. You can only select a time until 5:00 PM for 4 PM meeting.")

if meeting_time == "11 AM":
    start_time = datetime.combine(datetime.today(), datetime.strptime("11:00", "%H:%M").time())
    end_time = datetime.combine(datetime.today(), datetime.strptime("12:00", "%H:%M").time())
    available_times = pd.date_range(start=start_time, end=end_time, freq='5T').time
else:
    start_time = datetime.combine(datetime.today(), datetime.strptime("16:00", "%H:%M").time())
    end_time = datetime.combine(datetime.today(), datetime.strptime("17:00", "%H:%M").time())
    available_times = pd.date_range(start=start_time, end=end_time, freq='5T').time

attendance_data = []
attendance_df = pd.DataFrame(columns=["Name", "Email", "Phone", "Status", "Date and Time", "Meeting Time"])

for emp in employees:
    fullname, phone, email = emp
    st.write(f"### {fullname} - {email}")
    
    status = st.radio(
        f"Select status for {fullname}",
        ["Present", "Absent", "Off Duty", "On Call / Application"],
        key=f"status_{fullname}"
    )
    
    time = st.selectbox(
        f"Select time for {fullname}",
        available_times,
        key=f"time_{fullname}"
    )

    attendance_data.append({
        "fullname": fullname,
        "phone": phone,
        "email": email,
        "status": status,
        "date_time": datetime.combine(datetime.today(), time),
        "meeting_time": meeting_time
    })
    
    attendance_df = pd.concat([attendance_df, pd.DataFrame([{
        "Name": fullname, 
        "Email": email,
        "Phone": phone,
        "Status": status,
        "Date and Time": datetime.combine(datetime.today(), time),
        "Meeting Time": meeting_time
    }])], ignore_index=True)

st.write("### Attendance Data Preview:")
st.dataframe(attendance_df)

if st.button("Submit Attendance"):
    if attendance_data:
        for record in attendance_data:
            insert_attendance(record["fullname"], record["phone"], record["email"], record["status"], record["date_time"], record["meeting_time"])
        st.success("Attendance has been successfully recorded!")
    else:
        st.warning("No attendance selected. Please select an employee's status.")

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

csv = convert_df(attendance_df)
st.download_button(label="Download Attendance as CSV", data=csv, file_name="attendance.csv", mime="text/csv")

selected_date = st.date_input("Select a date to view previous attendance")

def get_attendance_for_date(date, meeting_time):
    conn = connect_db()
    cursor = conn.cursor()
    query = """
        SELECT fullname, phone, email, employee_status, date_time, meeting_time
        FROM employee_attendance
        WHERE date(date_time) = %s AND meeting_time = %s
    """
    cursor.execute(query, (date, meeting_time))
    attendance = cursor.fetchall()
    conn.close()
    return attendance

if selected_date:
    st.write(f"### Attendance for {selected_date} - 11 AM Meeting:")
    attendance_11am = get_attendance_for_date(selected_date, "11 AM")
    df_11am = pd.DataFrame(attendance_11am, columns=["Name", "Phone", "Email", "Status", "Date and Time", "Meeting Time"])
    st.dataframe(df_11am)

    if not df_11am.empty:
        csv_11am = convert_df(df_11am)
        st.download_button(label="Download 11 AM Attendance", data=csv_11am, file_name="attendance_11am.csv", mime="text/csv")

    st.write(f"### Attendance for {selected_date} - 4 PM Meeting:")
    attendance_4pm = get_attendance_for_date(selected_date, "4 PM")
    df_4pm = pd.DataFrame(attendance_4pm, columns=["Name", "Phone", "Email", "Status", "Date and Time", "Meeting Time"])
    st.dataframe(df_4pm)

    if not df_4pm.empty:
        csv_4pm = convert_df(df_4pm)
        st.download_button(label="Download 4 PM Attendance", data=csv_4pm, file_name="attendance_4pm.csv", mime="text/csv")
