import os
import io
import random as rnd
import openpyxl
from openpyxl.styles import Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd
from flask import Flask, request, redirect, flash, render_template, g, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from io import BytesIO

from flask_socketio import SocketIO, emit
from flask import request
import time

import webview
import json

# --- Custom Database Imports ---
from database import get_db_connection, init_db

# ------------------ Flask Setup ------------------
app = Flask(__name__)
app.secret_key = "secret"
app.config['DATABASE'] = 'sara.db'

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
OUTPUT_FOLDER = os.path.join(BASE_DIR, "output")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["OUTPUT_FOLDER"] = OUTPUT_FOLDER

app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
socketio = SocketIO(app, async_mode='threading')

active_sessions = {}


# --- Database Connection Management ---
with app.app_context():
    init_db()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def get_db():
    if 'db' not in g:
        g.db = get_db_connection()
    return g.db


#Authentication Connectivty:           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
IsLoggedIn  = False

# ------------------ Input Parsing (No Changes) ------------------
def parse_line(line: str):
    if not line or "#" not in line or "!" not in line or "@" not in line or "%" not in line or "^" not in line:
        raise ValueError(f"Bad line format: {line}")
    date_part, rest = line.split("#", 1)
    room_part, rest = rest.split("!", 1)
    paper_part, rest = rest.split("@", 1)
    year_part, rest = rest.split("%", 1)
    subject_part, rest = rest.split("^", 1)
    subject_type_part, separetion = rest.split("$", 1)
    return (date_part.strip(), room_part.strip(), paper_part.strip(), year_part.strip(), subject_part.strip(), subject_type_part.strip().lower(), separetion.strip())

# ------------------ Routes (Updated to SQLite) ------------------

@app.route("/roomSuggestion", methods=["POST"])
def room_suggestion():
    print("Room Suggestion Called")
    try:
        data = request.get_json()
        year = data.get("year", "")
        subject = data.get("subject", "")
        subject_type = data.get("subjectType", "")

        SubjectDictionary = {"PHYSA": "Physics", "CHMA": "Chemistry", "MTMA": "Mathematics", "ZOOA": "Zoology", "HISA": "History", "ENGA": "English", "BNGA": "Bengali", "SNSA": "Sanskrit", "PHILA": "Philosophy", "COMS": "Computer", "ECOA": "Economics", "POLA": "Political Science", "ACEM": "Applied Chemistry", "MCBA": "Microbiology", "INCA": "Industrial Chemistry"}

        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT student_data FROM StudentInfo WHERE Year LIKE ?", (f"%{year}%",))
        blob_row = cur.fetchone()

        if not blob_row or not blob_row['student_data']:
            return jsonify({"error": "No student data found for this year."}), 404

        df = pd.read_excel(BytesIO(blob_row['student_data']))
        subj_full = SubjectDictionary.get(subject, subject)
        rolls = []
        
        # This logic for parsing Excel remains the same
        if "PG" in year.upper():
            rolls = df[df["Subject"].str.contains(subj_full, case=False, na=False)]["Roll No"].tolist()
        elif subject_type.lower() == "major":
            rolls = df[df["Honours"].str.contains(subj_full, case=False, na=False)]["Roll Number"].tolist()
        elif subject_type.lower() == "minor":
            year_num = int(year.split("-")[1]) if "-" in year else 1
            general_col = "General1" if year_num % 2 != 0 else "General2"
            rolls = df[df[general_col].str.contains(subj_full, case=False, na=False)]["Roll Number"].tolist()
        else:
            year_num = int(year.split("-")[1]) if "-" in year else 1
            general_col = "General1" if year_num % 2 != 0 else "General2"
            rolls = df[df["Honours"].str.contains(subj_full, case=False, na=False) | df[general_col].str.contains(subj_full, case=False, na=False)]["Roll Number"].tolist()

        total_students = len(rolls)
        print("totalstudent",total_students)
        
        return jsonify({"rolls": rolls, "total_students": total_students})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def get_rolls_by_subject(year, subject, subject_type):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT student_data FROM StudentInfo WHERE Year LIKE ?", (f"%{year}%",))
    result = cursor.fetchone()
    
    if not result or not result['student_data']:
        return []

    excel_blob = result['student_data']
    wb = openpyxl.load_workbook(io.BytesIO(excel_blob))
    ws = wb.active
    headers = [cell.value for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    subj = subject.lower()
    rolls = []

    # --- UG/PG Excel parsing logic remains the same ---
    if "UG" in year.upper():
        roll_idx = headers.index("Roll Number"); honours_idx = headers.index("Honours"); gen1_idx = headers.index("General1"); gen2_idx = headers.index("General2")
        for row in ws.iter_rows(min_row=2, values_only=True):
            roll = row[roll_idx]; honours = str(row[honours_idx] or "").lower(); gen1 = str(row[gen1_idx] or "").lower(); gen2 = str(row[gen2_idx] or "").lower()
            if subject_type == "major":
                if subj in honours: rolls.append(roll)
            elif subject_type == "minor":
                year_num = int(year.split("-")[1])
                if year_num % 2 == 1:
                    if subj in gen1: rolls.append(roll)
                else:
                    if subj in gen2: rolls.append(roll)
            elif subject_type == "general":
                year_num = int(year.split("-")[1])
                if subj in honours: rolls.append(roll)
                if year_num % 2 == 1 and subj in gen1: rolls.append(roll)
                if year_num % 2 == 0 and subj in gen2: rolls.append(roll)
    elif "PG" in year.upper():
        roll_idx = headers.index("Roll No"); subj_idx = headers.index("Subject")
        for row in ws.iter_rows(min_row=2, values_only=True):
            roll = row[roll_idx]; subj_val = str(row[subj_idx] or "").lower()
            if subj in subj_val: rolls.append(roll)
    return rolls

def get_room_info(room_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT RoomId, TotalCapacity, BenchPerCol FROM RoomInfo WHERE RoomId = ?", (room_id.strip(),))
    result = cursor.fetchone()
    if result:
        bench_arrangement = []
        BenPerCols = result['BenchPerCol'].split(",")
        BenPerCols.reverse()
        for i in BenPerCols:
            oneCol = ["e"] * int(i)
            bench_arrangement.append(oneCol)
            bench_arrangement.append(oneCol.copy())
        return bench_arrangement
    else:
        print(f"No room found with ID '{room_id}'")
        return None

# --- Allocation and PDF Helpers (No Changes) ---
def can_place(seat_matrix, c, r, paper, sep):
    separation = int(sep)
    for dc in range(-1 * separation, separation):
        for dr in range(-1 * separation, separation):
            if dc == 0 and dr == 0: continue
            cc, rr = c + dc, r + dr
            if 0 <= cc < len(seat_matrix) and 0 <= rr < len(seat_matrix[cc]):
                neighbor = seat_matrix[cc][rr]
                if neighbor != "e" and neighbor[1] == paper: return False
    return True

def allocate_seats(seat_matrix, rolls, paper, year, sep, subject):
    if not seat_matrix: return seat_matrix, []
    for c in range(len(seat_matrix)):
        for r in range(len(seat_matrix[c])):
            if not rolls:
                seat_matrix.reverse(); return seat_matrix, []
            if seat_matrix[c][r] == "e" and can_place(seat_matrix, c, r, paper, sep):
                roll = rolls.pop(0)
                seat_matrix[c][r] = (roll, paper, year, subject)
    return seat_matrix, rolls

def export_pdf(pdf_path, totalRooms):
    """
    totalRooms = {
        "Room15-2025-08-25": (seat_matrix, date),
        ...
    }
    """
    doc = SimpleDocTemplate(pdf_path, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Constants for cell sizes
    SEAT_WIDTH = 80   # ~ 11 characters
    GUTTER_WIDTH = 15 # ~ 1 character
    ROW_HEIGHT = 25
    ROW_NUM_WIDTH = 25  # width for row number column

    for room, (seat_matrix, date) in totalRooms.items():
        # --- Header ---
        room_display = room.split("_")[0]  # original room number
        header_text = (
            "<b>RAMAKRISHNA MISSION VIDYAMANDIRA</b><br/>"
            "Howrah, Belur: 711202<br/><br/>"
            f"<b>Date:</b> {date} &nbsp;&nbsp;&nbsp; <b>Room:</b> {room_display}<br/>"
        )
        elements.append(Paragraph(header_text, styles["Title"]))
        elements.append(Spacer(1, 12))

        # --- Build seat grid ---
        max_rows = max(len(col) for col in seat_matrix)
        data = []

        for r in range(max_rows):
            row_data = []

            # Add row number in first column
            row_data.append(str(r + 1))

            for c in range(len(seat_matrix)):
                # Insert gutter after every 2 seat-columns
                if c > 0 and c % 2 == 0:
                    row_data.append("   ")

                if r < len(seat_matrix[c]):
                    seat = seat_matrix[c][r]
                    if seat == "e":  # empty seat with border
                        row_data.append("")  
                    elif seat is None:  # no seat at all
                        row_data.append(None)
                    else:  # filled seat
                        roll, paper, yr, subject = seat
                        row_data.append(f"{roll}\n{subject}-{yr}")
                else:
                    row_data.append(None)
            data.append(row_data)

        # --- Create custom colWidths (add row number col first) ---
        num_cols = len(data[0])
        colWidths = [ROW_NUM_WIDTH]  # first column for row numbers
        for c in range(1, num_cols):
            if all(row[c] == "   " or row[c] is None for row in data):
                colWidths.append(GUTTER_WIDTH)
            else:
                colWidths.append(SEAT_WIDTH)

        rowHeights = [ROW_HEIGHT for _ in range(len(data))]
        table = Table(data, colWidths=colWidths, rowHeights=rowHeights)

        # --- Styling ---
        style_commands = []

        

        # Merge gutters
        for c in range(1, num_cols):
            if all(row[c] == "   " for row in data):
                style_commands.append(("SPAN", (c, 0), (c, len(data)-1)))
                style_commands.append(("BOX", (c, 0), (c, len(data)-1), 0, colors.transparent))
                style_commands.append(("BACKGROUND", (c, 0), (c, len(data)-1), colors.white))

        for r, row in enumerate(data):
            for c, cell in enumerate(row):
                if c == 0:  # row number column → NO border
                    style_commands.append(("BOX", (c, r), (c, r), 0.5, colors.white))
                elif cell is None:  # no seat → no border
                    style_commands.append(("BOX", (c, r), (c, r), 0, colors.transparent))
                elif cell == "   ":  # gutter → no border
                    style_commands.append(("BOX", (c, r), (c, r), 0.5, colors.transparent))
                else:  # filled seat or empty seat → border
                    style_commands.append(("GRID", (c, r), (c, r), 0.5, colors.black))

        style_commands.append(("ALIGN", (0, 0), (-1, -1), "CENTER"))
        style_commands.append(("VALIGN", (0, 0), (-1, -1), "MIDDLE"))
        table.setStyle(TableStyle(style_commands))

        elements.append(table)
        elements.append(PageBreak())

    doc.build(elements)


# --- CRUD Routes (Updated to SQLite) ---

@app.route("/Roominfo", methods=["GET", "POST"])
def Roominfo():
    conn = get_db(); cursor = conn.cursor()
    if request.method == "POST":
        room_id, capacity, benches = request.form.get("RoomId"), request.form.get("TotalCapacity"), request.form.get("BenchPerCol")
        if not room_id or not capacity or not benches: return "❌ Missing fields", 400
        
        cursor.execute("SELECT * FROM RoomInfo WHERE RoomId=?", (room_id,))
        if cursor.fetchone():
            cursor.execute("UPDATE RoomInfo SET TotalCapacity=?, BenchPerCol=? WHERE RoomId=?", (capacity, benches, room_id))
        else:
            cursor.execute("INSERT INTO RoomInfo (RoomId, TotalCapacity, BenchPerCol) VALUES (?, ?, ?)", (room_id, capacity, benches))
        conn.commit()
        return redirect("/Roominfo")
    
    if IsLoggedIn == True:
        cursor.execute("SELECT * FROM RoomInfo")
        rooms = [dict(row) for row in cursor.fetchall()]
        return render_template("roominfo.html", data=rooms)
    else:
        return redirect('/LoginBar')

@app.route("/Roominfo/delete", methods=["POST"])
def delete_room():
    room_id = request.get_json().get("RoomId")
    if not room_id: return jsonify({"error": "RoomId is required"}), 400
    conn = get_db()
    conn.execute("DELETE FROM RoomInfo WHERE RoomId=?", (room_id,))
    conn.commit()
    return jsonify({"success": True, "RoomId": room_id})

@app.route("/Studentinfo", methods=["POST", "GET"])
def Studentinfo():
    conn = get_db(); cursor = conn.cursor()
    if request.method == "POST":
        institute, year, file = "RAMAKRISHNA MISSION VIDYAMANDIRA", request.form.get("Year"), request.files.get("StudentDataFile")
        if not file: flash("No file uploaded"); return redirect("/Studentinfo")
        file_data = file.read()
        
        # SQLite's equivalent of UPSERT
        cursor.execute("""
            INSERT INTO StudentInfo (InstituteName, Year, student_data) VALUES (?, ?, ?)
            ON CONFLICT(Year) DO UPDATE SET
                InstituteName=excluded.InstituteName,
                student_data=excluded.student_data
        """, (institute, year, file_data))
        conn.commit()
        flash("Student info added/updated successfully")
        return redirect("/Studentinfo")
    
    # Only select columns needed for display (exclude BLOB)
    if IsLoggedIn:
        cursor.execute("SELECT InstituteName, Year FROM StudentInfo")
        student_records = [dict(row) for row in cursor.fetchall()]
        return render_template("studentinfo.html", data=student_records, columns=["InstituteName", "Year","StudentData"])
    else:
        return redirect('/LoginBar')

@app.route("/Studentinfo/delete", methods=["POST"])
def delete_studentinfo_route():
    year = request.get_json().get("Year")
    if not year: return jsonify({"error": "Year is required"}), 400
    conn = get_db()
    conn.execute("DELETE FROM StudentInfo WHERE Year = ?", (year,))
    conn.commit()
    return jsonify({"success": True, "message": f"Record for Year {year} deleted."})

@app.route("/developers")
def developers():
    return render_template("devteam.html")

# --- Main Allocation Route ---
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        SubjectDictionary = {"PHYSA": "Physics", "CHMA": "Chemistry", "MTMA": "Mathematics","ZOOA": "Zoology","HISA": "History", "ENGA": "English", "BNGA": "Bengali", "SNSA": "Sanskrit", "PHILA": "Philosophy", "COMS": "Computer", "ECOA": "Economics", "POLA": "Political Science", "ACEM":"Applied Chemistry", "MCBA": "Microbiology","INCA": "Industrial Chemistry"}
        totalRooms = {}; file = request.files.get("file")
        if not file: flash("No file uploaded"); return redirect(request.url)
        
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
        file.save(filepath)
        with open(filepath, "r") as f: lines = f.read().splitlines()
        
        rnd.shuffle(lines)
        for line in lines:
            if not line.strip(): continue
            date, room, paper, year, subject, subject_type, separation = parse_line(line)
            rooms = room.split(",")
            rolls = get_rolls_by_subject(year, SubjectDictionary[subject], subject_type)
            while rolls and rooms:
                room_key = f"{rooms[0]}_{date.replace('/', '-')}"
                if room_key in totalRooms:
                    seat_matrix = totalRooms[room_key][0]
                else:
                    seat_matrix = get_room_info(rooms.pop(0))
                    if not seat_matrix: continue
                prev_len = len(rolls)
                seat_matrix, rolls = allocate_seats(seat_matrix, rolls, paper, year, separation, subject)
                totalRooms[room_key] = (seat_matrix, date)
                if len(rolls) == prev_len:
                    print("⚠️ Cannot place remaining rolls in available rooms"); break
        
        pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], "All_Seating_Allotments.pdf")
        export_pdf(pdf_path, totalRooms)
        return render_template("pdf-viewer.html", pdf_files=["All_Seating_Allotments.pdf"])
    
    if IsLoggedIn :
        conn = get_db(); cursor = conn.cursor()
        cursor.execute("SELECT RoomId, TotalCapacity FROM RoomInfo")
        rooms = [dict(row) for row in cursor.fetchall()]
        return render_template("index.html", rooms=rooms)
    else:
        return redirect('/LoginBar')

@app.route("/LoginBar", methods=["GET", "POST"])
def LogIn():
    global IsLoggedIn
    if request.method == "POST":
        GivenPassword = request.form.get('password')
        ActualPassword = ""
        filename = os.path.join(app.static_folder, 'Authentication.json')
        with open(filename, 'r') as f:
            data = json.load(f)
            ActualPassword = data.get('password','')
        
        if ActualPassword == GivenPassword:
            IsLoggedIn = True
        else:
            return render_template('login.html', error="wrong password")
        return redirect('/')
    if IsLoggedIn:
        return redirect('/LoginBar')
    
    return render_template("login.html")
        


@app.route("/preview/<filename>")
def preview_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename)

@socketio.on('connect')
def handle_connect():
    print("Client connected:", request.sid)
    active_sessions[request.sid] = {'totalRooms': {}}

@socketio.on('disconnect')
def handle_disconnect():
    print("Client disconnected:", request.sid)
    active_sessions.pop(request.sid, None)

@socketio.on('allocate_paper')
def handle_allocate_paper(data):
    sid = request.sid
    session_data = active_sessions.get(sid)
    if not session_data:
        emit('allocation_result', {'status': 'error', 'message': 'Session expired. Please reload.'})
        return
        
    totalRooms = session_data['totalRooms']
    date = data.get('date', '')
    rooms = list(data.get('rooms', []))
    paper = data.get('paperName', '')
    year = data.get('year', '')
    subject = data.get('subject', '')
    separation = int(data.get('separation', 1))
    rolls = list(data.get('_rolls', []))
    
    while rolls and rooms:
        room_key = f"{rooms[0]}_{date.replace('/', '-')}"
        if room_key in totalRooms:
            seat_matrix = totalRooms[room_key][0]
        else:
            seat_matrix = get_room_info(rooms[0])
            if not seat_matrix: 
                rooms.pop(0)
                continue
                
        prev_len = len(rolls)
        seat_matrix, rolls = allocate_seats(seat_matrix, rolls, paper, year, separation, subject)
        totalRooms[room_key] = (seat_matrix, date)
        
        if len(rolls) == prev_len:
            print(f"⚠️ Cannot place remaining rolls in {rooms[0]}")
            rooms.pop(0)
            
    pdf_filename = f"preview_{sid}.pdf"
    pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
    export_pdf(pdf_path, totalRooms)
    
    emit('allocation_result', {'status': 'success', 'pdf_url': f'/preview/{pdf_filename}?t={time.time()}'})

@socketio.on('finish_allocation')
def handle_finish_allocation():
    sid = request.sid
    session_data = active_sessions.get(sid)
    if not session_data:
        emit('finish_result', {'status': 'error', 'message': 'Session expired'})
        return
        
    pdf_filename = f"Final_Allocation_{sid}.pdf"
    pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_filename)
    if session_data['totalRooms']:
        export_pdf(pdf_path, session_data['totalRooms'])
    
    emit('finish_result', {'status': 'success', 'pdf_url': f'/preview/{pdf_filename}?t={time.time()}', 'download_url': f'/download/{pdf_filename}'})


@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# ------------------ Run ------------------
# def start_flask(**kwargs):
#     app.run(**kwargs)

# This is the new main entry point for the desktop app
# if __name__ == "__main__":
    
#     browser_path = None
#     # If on Linux, you may need to specify the browser path explicitly
#     if platform.system() == "Linux":
#         # Edit this path to the location of your Chrome/Chromium executable
#         # Common paths: '/usr/bin/google-chrome-stable', '/usr/bin/chromium-browser'
#         browser_path = "/snap/bin/brave"
#     icon_path = "static/img/rasa1.png"
#     FlaskUI(
#         server=start_flask,
#         server_kwargs={"host": "127.0.0.1", "port": 5000},
#         app="flask",
#         width=1000,
#         fullscreen=False,
#         height=600,
#         browser_path=browser_path, # This tells the app where to find the browser
#     ).run()

# if __name__ == "__main__":
#     webview.settings['ALLOW_DOWNLOADS'] = True
#     webview.create_window("SARA", app, height=900, width=1200)
#     webview.start(icon="static/img/SARA-FAVICON.ico")

if __name__ == "__main__":
    app.run(debug=False)
    