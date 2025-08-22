from flask import Flask, request, render_template, jsonify
import random

app = Flask(__name__)

# Departments
DEPARTMENTS = ["PHYS", "CHEM", "MATH", "MCBA", "COMS", "INCH", "ECON", "ZOOL",
               "BENG", "ENG", "SANS", "HIS", "PHIL", "POLS"]

# Assume each hall: 2 columns x 10 benches x 2 seats = 40 seats total
HALLS = {f"HALL-{i}": {"columns": 2, "benches_per_col": 10, "seats_per_bench": 2}
         for i in range(1, 36)}


# Helper: Parse roll number range string like "1001-1010,2001-2005"
def parse_roll_range(roll_range_text):
    students = []
    ranges = roll_range_text.split(",")
    for r in ranges:
        start, end = map(int, r.strip().split("-"))
        students.extend(list(range(start, end + 1)))
    return students


# Seat allocation logic
def allocate_seats(hall_name, students):
    hall = HALLS[hall_name]
    rows = hall["benches_per_col"]
    cols = hall["columns"] * hall["seats_per_bench"]  # 2 cols * 2 seats = 4 per row

    # Make seat matrix (rows x cols)
    seat_matrix = [[None for _ in range(cols)] for _ in range(rows)]

    # Pick 3 random departments
    chosen_depts = random.sample(DEPARTMENTS, 3)

    # Assign students cyclically A-B-C
    dept_cycle = []
    while len(dept_cycle) < len(students):
        dept_cycle.extend(chosen_depts)

    idx = 0
    for r in range(rows):
        for c in range(cols):
            if idx < len(students):
                seat_matrix[r][c] = {
                    "roll": students[idx],
                    "dept": dept_cycle[idx % len(chosen_depts)]
                }
                idx += 1

    return seat_matrix, chosen_depts


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        dept = request.form.get("department")
        year = request.form.get("year")
        exam_date = request.form.get("exam_date")
        exam_time = request.form.get("exam_time")
        roll_range = request.form.get("roll_range")
        hall = request.form.get("hall")

        students = parse_roll_range(roll_range)
        seat_matrix, chosen = allocate_seats(hall, students)

        return render_template("seating.html", hall=hall, seat_matrix=seat_matrix,
                               chosen=chosen, exam_date=exam_date,
                               exam_time=exam_time, dept=dept, year=year)

    return render_template("seatallot_new.html", halls=HALLS.keys(), departments=DEPARTMENTS)


if __name__ == "__main__":
    app.run(debug=True)
