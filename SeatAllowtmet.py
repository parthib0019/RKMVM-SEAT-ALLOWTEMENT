import os
import pymysql
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash
from werkzeug.utils import secure_filename
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import numpy as np
from itertools import zip_longest

# ------------------ Flask Config ------------------
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = "uploads"
app.config['OUTPUT_FOLDER'] = "output"
app.secret_key = "supersecret"

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

# ------------------ Database ------------------
def get_room_info(room_id):
    try:
        # Connect to MySQL
        conn = pymysql.connect(
            host="localhost",       # or "127.0.0.1"
            user="root",            # default XAMPP MySQL user
            password="",            # set your password here if you have one
            database="ExamSeatAllowtment"   # <-- replace with your database name
        )
        cursor = conn.cursor()

        # Take input from terminal
        room_id = room_id.strip()

        # Query the database
        query = "SELECT RoomId, TotalCapacity, BenchPerCol FROM RoomInfo WHERE RoomId = %s"
        cursor.execute(query, (room_id,))

        result = cursor.fetchone()

        if result:
            # Bench arrangement
            bench_arrangement = []
            BenPerCols = result[2].split(",")
            BenPerCols.reverse()
            for i in BenPerCols:
                oneCol =[]
                for j in range(int(i)):
                    oneCol.append("e")
                bench_arrangement.append(oneCol)
                bench_arrangement.append(oneCol)
            return bench_arrangement
        else:
            print(f"No room found with ID '{room_id}'")
        
        cursor.close()
        conn.close()

    except pymysql.Error as err:
        print(f"Error: {err}")


# ------------------ Parsing ------------------
def parse_line(line: str):
    subj_year_rolls, date_room = line.split("!")
    subj_year, roll_ranges = subj_year_rolls.split("$")
    subject, year = subj_year.split("#")
    roll_range, date, room = roll_ranges, *date_room.split("@")
    return subject.strip(), year.strip(), roll_range.strip(), date.strip(), room.strip()

def expand_rolls(roll_text: str):
    rolls = []
    parts = roll_text.split(",")
    for part in parts:
        if "-" in part:
            start, end = map(int, part.split("-"))
            rolls.extend(range(start, end+1))
        else:
            rolls.append(int(part))
    return rolls

# ------------------ Allocation ------------------
def can_place(seat_matrix, c, r, dept):
    for dc in [-1, 0, 1]:
        for dr in [-1, 0, 1]:
            if dc == 0 and dr == 0:
                continue
            cc = c + dc
            rr = r + dr
            if 0 <= cc < len(seat_matrix) and 0 <= rr < len(seat_matrix[cc]):
                neighbor = seat_matrix[cc][rr]
                if neighbor != "e" and neighbor[1] == dept:
                    return False    
    return True



def allocate_seats(seat_matrix, rolls, dept, year):
    if not seat_matrix:
        return seat_matrix

    # Work on a mutable list of rolls
    rolls = list(rolls)

    for c in range(len(seat_matrix)):          # loop over columns
        for r in range(len(seat_matrix[c])):   # loop benches in column
            if not rolls:                      # stop if no rolls left
                for i in seat_matrix:print(i)
                return seat_matrix

            if seat_matrix[c][r] == "e":
                if can_place(seat_matrix, c, r, dept):
                    roll = rolls.pop(0)        # take the first roll and remove it
                    seat_matrix[c][r] = (roll, dept, year)
    

    return seat_matrix







# ------------------ PDF Export ------------------

def rotate_for_pdf(seat_matrix):
    """
    Convert column-based seat_matrix (jagged lists) into row-based matrix for PDF.
    """
    rotated = list(zip_longest(*seat_matrix, fillvalue="e"))
    return [list(row) for row in rotated]

def export_pdf(filename, seat_matrix, subject, year, date, room):
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    # Header
    elements.append(Paragraph(f"<b>Room {room} | {date} | {subject} {year}</b>", styles["Heading2"]))
    elements.append(Spacer(1, 12))

    # Rotate seat_matrix for PDF printing
    pdf_matrix = rotate_for_pdf(seat_matrix)

    # Convert seat_matrix into table data
    data = []
    for row in pdf_matrix:
        row_data = []
        for seat in row:
            if seat == "e":
                row_data.append("")   # empty cell
            elif isinstance(seat, tuple):
                if len(seat) == 3:
                    roll, dept, yr = seat
                elif len(seat) == 2:
                    roll, dept = seat
                    yr = ""
                else:
                    roll, dept, yr = "", "", ""
                row_data.append(f"{roll}\n{dept}-{yr}")
            else:
                row_data.append("")   # fallback
        data.append(row_data)

    # Create table
    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
    ]))

    elements.append(table)
    doc.build(elements)



# ------------------ Routes ------------------
@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        file = request.files.get("file")
        if not file:
            flash("No file uploaded")
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        with open(filepath, "r") as f:
            lines = f.read().splitlines()

        pdf_files = []
        for line in lines:
            if not line.strip():
                continue
            subject, year, roll_range, date, room = parse_line(line)
            rolls = expand_rolls(roll_range)
            seat_matrix = get_room_info(room)
            if not seat_matrix:
                print(f"⚠️ No room info found for Room {room}")
                continue
            seat_matrix = allocate_seats(seat_matrix, rolls, subject, year)


            pdf_name = f"{subject}_{year}_{room}.pdf".replace(" ", "_")
            pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], pdf_name)
            export_pdf(pdf_path, seat_matrix, subject, year, date, room)
            pdf_files.append(pdf_name)

        return render_template("seating.html", pdf_files=pdf_files)

    return render_template("seatallot_new.html")

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# ------------------ Run ------------------
if __name__ == "__main__":
    app.run(debug=True)
