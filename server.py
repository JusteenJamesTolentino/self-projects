from flask import Flask, jsonify, render_template
import threading
import asyncio
import websockets
import socket
import json
import uuid
import random
import time

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/game')
def game():
    return render_template('game.html')


@app.route('/snake')
@app.route('/snakes')
def snake_page():
    host = f"ws://localhost:{websocket_port or 6789}"
    return render_template('snake.html', websocket_host=host)


@app.route('/api/data', methods=['GET'])
def get_data():
    return jsonify({"message": "Hello, World!"})


@app.route('/ws-port', methods=['GET'])
def ws_port():
    return jsonify({'port': websocket_port})


clients = {}
players = {}
rooms = {}
state_lock = asyncio.Lock()

websocket_port = None

GRID_W = 28
GRID_H = 20
CELL_SIZE = 18
TICK = 0.15


def random_empty_cell(room=None):
    for _ in range(200):
        x = random.randrange(1, GRID_W - 1)
        y = random.randrange(1, GRID_H - 1)
        occupied = False
        for p in players.values():
            if room is not None and p.get('room') != room:
                continue
            for sx, sy in p.get('snake', []):
                if sx == x and sy == y:
                    occupied = True
                    break
            if occupied:
                break
        if occupied:
            continue
        if room and room in rooms:
            clash = any(f[0] == x and f[1] == y for f in rooms[room].get('food', []))
            if clash:
                continue
        return [x, y]
    return [random.randrange(1, GRID_W - 1), random.randrange(1, GRID_H - 1)]


async def broadcast_room_state(room_name):
    room_info = rooms.get(room_name, {'food': [], 'running': False})
    players_subset = {pid: p for pid, p in players.items() if p.get('room') == room_name}
    state = {
        'type': 'state',
        'players': players_subset,
        'food': room_info.get('food', []),
        'w': GRID_W,
        'h': GRID_H,
        'room': room_name,
        'running': room_info.get('running', False),
    }
    data = json.dumps(state, default=lambda o: list(o) if isinstance(o, set) else o)
    webs = list(clients.keys())
    for ws in webs:
        try:
            pid = clients.get(ws)
            if not pid:
                continue
            p = players.get(pid)
            if not p:
                continue
            if p.get('room') != room_name:
                continue
            await ws.send(data)
        except Exception:
            pass


async def game_loop():
    while True:
        try:
            async with state_lock:
                for room_name, room_info in rooms.items():
                    if 'food' not in room_info:
                        room_info['food'] = []
                    while len(room_info['food']) < 3:
                        room_info['food'].append(random_empty_cell(room=room_name))

                for room_name, room_info in list(rooms.items()):
                    running = room_info.get('running', False)
                    if not running:
                        continue
                    for pid, p in list(players.items()):
                        if p.get('room') != room_name:
                            continue
                        if not p.get('alive'):
                            continue
                        hx, hy = p['snake'][0]
                        dx, dy = p.get('dir', [1, 0])
                        nx, ny = hx + dx, hy + dy
                        if nx < 0 or nx >= GRID_W or ny < 0 or ny >= GRID_H:
                            p['alive'] = False
                            continue
                        if [nx, ny] in p['snake']:
                            p['alive'] = False
                            continue
                        collided = False
                        for oid, op in players.items():
                            if op.get('room') != room_name:
                                continue
                            if oid == pid:
                                continue
                            if [nx, ny] in op.get('snake', []):
                                collided = True
                                break
                        if collided:
                            p['alive'] = False
                            continue

                        p['snake'].insert(0, [nx, ny])
                        ate = False
                        for f in list(room_info.get('food', [])):
                            if f[0] == nx and f[1] == ny:
                                try:
                                    room_info['food'].remove(f)
                                except ValueError:
                                    pass
                                p['score'] = p.get('score', 0) + 1
                                ate = True
                                break
                        if not ate:
                            if len(p['snake']) > 1:
                                p['snake'].pop()

                for room_name in list(rooms.keys()):
                    await broadcast_room_state(room_name)
        except Exception as e:
            print(f"[GAME] loop exception: {e}")
        await asyncio.sleep(TICK)


async def ws_handler(websocket):
    pid = str(uuid.uuid4())
    clients[websocket] = pid
    try:
        remote = websocket.remote_address
    except Exception:
        remote = None
    print(f"[WS] new connection pid={pid} remote={remote}")

    async with state_lock:
        rooms.setdefault('lobby', {'food': [], 'running': False})
        players[pid] = {
            'id': pid,
            'name': f'Player-{pid[:4]}',
            'snake': [[random.randrange(4, 8), random.randrange(4, 8)]],
            'dir': [1, 0],
            'alive': True,
            'score': 0,
            'color': '#{:06x}'.format(random.randint(0x444444, 0xffffff)),
            'room': 'lobby'
        }

    try:
        await websocket.send(json.dumps({'type': 'welcome', 'id': pid}))
        async for message in websocket:
            try:
                data = json.loads(message)
            except Exception:
                print(f"[WS] pid={pid} received invalid JSON")
                continue
            mtype = data.get('type')
            # quick ping/pong to allow client latency measurement
            if mtype == 'ping':
                try:
                    ts = data.get('ts')
                    await websocket.send(json.dumps({'type': 'pong', 'ts': ts}))
                except Exception:
                    pass
                continue
            async with state_lock:
                if mtype == 'join':
                    players[pid]['name'] = data.get('name', players[pid]['name'])
                    room = data.get('room')
                    if room:
                        players[pid]['room'] = room
                        rooms.setdefault(room, {'food': [], 'running': False})
                    print(f"[WS] pid={pid} JOIN room={players[pid]['room']} name={players[pid]['name']}")
                elif mtype == 'start':
                    room = data.get('room') or players[pid].get('room')
                    rooms.setdefault(room, {'food': [], 'running': False})
                    rooms[room]['running'] = True
                    for opid, op in players.items():
                        if op.get('room') == room:
                            op['snake'] = [[random.randrange(4, 8), random.randrange(4, 8)]]
                            op['dir'] = [1, 0]
                            op['alive'] = True
                            op['score'] = 0
                    rooms[room]['food'] = []
                    print(f"[WS] pid={pid} START room={room}")
                elif mtype == 'dir':
                    d = data.get('dir')
                    if d == 'up':
                        players[pid]['dir'] = [0, -1]
                    elif d == 'down':
                        players[pid]['dir'] = [0, 1]
                    elif d == 'left':
                        players[pid]['dir'] = [-1, 0]
                    elif d == 'right':
                        players[pid]['dir'] = [1, 0]
                    print(f"[WS] pid={pid} DIR {d}")
    except websockets.exceptions.ConnectionClosed:
        pass
    except Exception as e:
        print(f"[WS] pid={pid} handler exception: {e}")
    finally:
        print(f"[WS] connection closed pid={pid}")
        try:
            async with state_lock:
                if websocket in clients:
                    del clients[websocket]
                if pid in players:
                    del players[pid]
        except Exception:
            pass


async def ws_main(port=6789):
    print(f"Starting WebSocket server on 0.0.0.0:{port}")
    server = await websockets.serve(ws_handler, '0.0.0.0', port)
    await game_loop()
    await server.wait_closed()


def find_free_port(preferred=(6789, 6790)):
    for p in preferred:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', p))
                return p
            except OSError:
                continue
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('0.0.0.0', 0))
        return s.getsockname()[1]


def start_ws_server():
    port = find_free_port()
    global websocket_port
    websocket_port = port
    try:
        ws_ver = getattr(websockets, '__version__', 'unknown')
    except Exception:
        ws_ver = 'unknown'
    print(f"Starting WebSocket server on port {port} (preferred 6789/6790) - websockets v{ws_ver}")
    try:
        asyncio.run(ws_main(port=port))
    except OSError as e:
        print(f"Failed to start WebSocket server on port {port}: {e}")


def start_servers():
    ws_thread = threading.Thread(target=start_ws_server, daemon=True)
    ws_thread.start()
    app.run(debug=True, host='0.0.0.0', port=5000)


if __name__ == '__main__':
    start_servers()