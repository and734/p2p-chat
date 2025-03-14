import os
import secrets
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_socketio import SocketIO, join_room, leave_room, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', secrets.token_hex(16))  # Use environment variable or generate
socketio = SocketIO(app)

# Store room information (name: [user1_sid, user2_sid])
rooms = {}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/room', methods=['POST'])
def create_or_join_room():
    room_name = request.form.get('roomName')

    if not room_name or room_name.strip() == "":
        flash("Please enter a valid room name.", "error")
        return redirect(url_for('index'))

    room_name = room_name.strip()

    if room_name in rooms:
        if len(rooms[room_name]) >= 2:
            return jsonify({'status': 'full', 'message': 'Room is full.'})
        else:
             return jsonify({'status': 'join', 'roomName': room_name})
    else:
         return jsonify({'status': 'create', 'roomName': room_name})


@socketio.on('connect')
def handle_connect():
    print(f'Client connected: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Client disconnected: {request.sid}')
    for room_name, participants in rooms.items():
        if request.sid in participants:
            participants.remove(request.sid)
            if not participants:  # If the room is empty, remove it
                del rooms[room_name]
            else:  # Notify the other user
                 socketio.emit('user_disconnected', {'sid': request.sid}, room=room_name)
            break


@socketio.on('join')
def handle_join(data):
    room_name = data['roomName']
    join_room(room_name)

    if room_name not in rooms:
        rooms[room_name] = []

    if request.sid not in rooms[room_name]: # Prevent duplicate additions on reconnect
         rooms[room_name].append(request.sid)

    emit('joined', {'sid': request.sid, 'room': room_name, 'num_participants': len(rooms[room_name])}, room=request.sid)  #To current User

    # Notify other participants (if any)
    if len(rooms[room_name]) > 1:
        emit('new_user', {'sid': request.sid}, room=room_name, include_self=False)


@socketio.on('offer')
def handle_offer(data):
    recipient_sid = data['recipientSid']
    offer = data['offer']
    emit('offer', {'senderSid': request.sid, 'offer': offer}, to=recipient_sid)

@socketio.on('answer')
def handle_answer(data):
    recipient_sid = data['recipientSid']
    answer = data['answer']
    emit('answer', {'senderSid': request.sid, 'answer': answer}, to=recipient_sid)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    recipient_sid = data['recipientSid']
    candidate = data['candidate']
    emit('ice_candidate', {'senderSid': request.sid, 'candidate': candidate}, to=recipient_sid)

@socketio.on('error_media')
def handle_media_error(data):
   emit('media_error', {'message': data.get('message', 'Media error occurred.')}, room=request.sid)

if __name__ == '__main__':
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
