set -euo pipefail
PORT=7860
HOST=0.0.0.0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --port)
      PORT="$2"; shift 2;;
    --host)
      HOST="$2"; shift 2;;
    -h|--help)
      echo "Usage: ./run.sh [--port PORT] [--host HOST]"; exit 0;;
    *)
      echo "Unknown arg: $1"; exit 1;;
  esac
done

if [[ -x "./myenv/bin/python" ]]; then
  PY=./myenv/bin/python
else
  PY=$(which python3 || which python)
fi
echo "Using python: $PY"

exec "$PY" run_gradio.py -- --server_name "$HOST" --server_port "$PORT"
