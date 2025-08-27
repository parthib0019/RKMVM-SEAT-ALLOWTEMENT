import os
import pymysql
from flask import Flask, request, render_template, send_from_directory, redirect, url_for, flash
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from werkzeug.utils import secure_filename
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
import numpy as np
from itertools import zip_longest
import random as rnd

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
                bench_arrangement.append(oneCol.copy())
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
    #print(f"Checking placement at ({c}, {r}) for dept {dept}")
    separation = 2
    for dc in range(-1*separation, separation):
        for dr in range(-1*separation, separation):
            if dc == 0 and dr == 0:
                continue
            cc = c + dc
            rr = r + dr
            if 0 <= cc < len(seat_matrix) and 0 <= rr < len(seat_matrix[cc]):
                neighbor = seat_matrix[cc][rr]
                #print(f"Neighbor at ({cc}, {rr}): {neighbor}")
                if neighbor != "e" and neighbor[1] == dept:
                    return False    
    return True



def allocate_seats(seat_matrix, rolls, dept, year):
    if not seat_matrix:
        return seat_matrix

    #rolls = list(rolls)  # make mutable copy

    for c in range(len(seat_matrix)):          # loop over columns
        for r in range(len(seat_matrix[c])):   # loop benches in column
            if not rolls:                      # stop if no rolls left
                seat_matrix.reverse()
                return seat_matrix

            if seat_matrix[c][r] == "e" and can_place(seat_matrix, c, r, dept):
                roll = rolls.pop(0)            # assign one roll only
                seat_matrix[c][r] = (roll, dept, year)
    return seat_matrix




# ------------------ PDF Export ------------------

def rotate_for_pdf(seat_matrix):
    """
    Convert column-based seat_matrix (jagged lists) into row-based matrix for PDF.
    """
    rotated = list(zip_longest(*seat_matrix, fillvalue="e"))
    return [list(row) for row in rotated]

def export_pdf(filename, totalRooms):
    """
    Export all rooms and dates into a single multi-page PDF
    totalRooms = { "room_date": (seat_matrix, date, subject, year) }
    """
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()

    for room_key, (seat_matrix, date) in totalRooms.items():
        # --- Header ---
        elements.append(Paragraph("<b>RAMAKRISHNA MISSION VIDYAMANDIRA</b>", styles["Title"]))
        elements.append(Paragraph("Howrah, Belur: 711202", styles["Heading3"]))
        elements.append(Spacer(1, 12))
        elements.append(Paragraph(f"<b>Date:</b> {date} &nbsp;&nbsp;&nbsp; <b>Room:</b> {room_key.split('_')[0]}", styles["Heading4"]))
        elements.append(Spacer(1, 12))

        # --- Build seat table ---
        max_rows = max(len(col) for col in seat_matrix)

        data = []
        for r in range(max_rows):
            row_data = []
            for c in range(len(seat_matrix)):
                if r < len(seat_matrix[c]):
                    seat = seat_matrix[c][r]
                    if seat != "e":
                        roll, dept, yr = seat
                        row_data.append(f"{roll}\n{dept}-{yr}")
                    else:
                        row_data.append("")
                else:
                    row_data.append(None)

                # Add a blank spacer column after every 2 bench-columns
                if (c + 1) % 2 == 0 and c != len(seat_matrix) - 1:
                    row_data.append("")  # spacer column

            data.append(row_data)

        # --- Table formatting ---
        table = Table(data)

        style_commands = [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),  # full grid for all seats
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]

        # Handle spacer columns → merge them vertically into one wide blank column
        for c in range(len(data[0])):  # iterate over columns
            # detect spacer columns (all cells = "")
            if all(row[c] == "" for row in data):
                style_commands.append(("SPAN", (c, 0), (c, len(data)-1)))   # merge vertically
                style_commands.append(("LINEBEFORE", (c, 0), (c, len(data)-1), 0, colors.white))
                style_commands.append(("LINEAFTER", (c, 0), (c, len(data)-1), 0, colors.white))
                style_commands.append(("BACKGROUND", (c, 0), (c, len(data)-1), colors.white))

        # Handle None cells → remove borders
        for r, row in enumerate(data):
            for c, cell in enumerate(row):
                if cell is None:
                    style_commands.append(("BOX", (c, r), (c, r), 0, colors.white))

        table.setStyle(TableStyle(style_commands))



        elements.append(table)
        elements.append(PageBreak())  # new page per room/date

    doc.build(elements)



# ------------------ Routes ------------------

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        totalRooms = {}                      # {room_id: (seat_matrix, date, subject-year list)}
        file = request.files.get("file")
        if not file:
            flash("No file uploaded")
            return redirect(request.url)
        
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        with open(filepath, "r") as f:
            lines = f.read().splitlines()

        rnd.shuffle(lines)
        pdf_files = []
        for line in lines:
            if not line.strip():
                continue
            print(f"Processing line: {line}")
            subject, year, roll_range, date, room = parse_line(line)
            rolls = expand_rolls(roll_range)
            room_key = f"{room}_{date.replace('/', '-')}"   # unique key per room per date

            if room_key in totalRooms:
                # Same room on same date → fetch old matrix and update
                seat_matrix = totalRooms[room_key][0]
                seat_matrix = allocate_seats(seat_matrix, rolls, subject, year)
                totalRooms[room_key] = (seat_matrix, date)

            else:
                # Either new room OR same room but different date → fresh start
                seat_matrix = get_room_info(room)
                if not seat_matrix:
                    print(f"⚠️ No room info found for Room {room}")
                    continue
                seat_matrix = allocate_seats(seat_matrix, rolls, subject, year)
                totalRooms[room_key] = (seat_matrix, date)


        print(totalRooms)
        # After filling totalRooms
        pdf_path = os.path.join(app.config['OUTPUT_FOLDER'], "All_Seating_Allotments.pdf")
        export_pdf(pdf_path, totalRooms)
        pdf_files = ["All_Seating_Allotments.pdf"]


        return render_template("seating.html", pdf_files=pdf_files)

    return render_template("seatallot_new.html")

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config['OUTPUT_FOLDER'], filename, as_attachment=True)

# ------------------ Run ------------------
if __name__ == "__main__":
    app.run(debug=True)
