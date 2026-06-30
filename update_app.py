import re

with open("app.py", "r") as f:
    content = f.read()

# Add socketio imports
import_str = """
from flask_socketio import SocketIO, emit
from flask import request
import time
"""
content = content.replace("from io import BytesIO", "from io import BytesIO\n" + import_str)

# Initialize socketio
init_str = """
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
socketio = SocketIO(app)

active_sessions = {}
"""
content = content.replace("app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0", init_str)

# Add preview route and socketio events
events_str = """
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

"""

content = content.replace("def download_file(filename):", events_str + "\ndef download_file(filename):")

# Change app.run to socketio.run
content = content.replace("app.run(debug=False)", "socketio.run(app, debug=False)")

with open("app.py", "w") as f:
    f.write(content)

