"""桌面入口（exe 主入口）：本地 uvicorn 服务 + pywebview 窗口，回退系统浏览器。

环境判定：能 import webview 且窗口启动成功 → 桌面模式；
否则自动打开默认浏览器，进程常驻直到 Ctrl+C。
"""
import socket
import threading
import time
import webbrowser
from .core import config
from .models import database


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]


def _start_server(port):
    import uvicorn
    from .api.app import app
    cfg = uvicorn.Config(app, host='127.0.0.1', port=port, log_level='warning',
                         loop='asyncio', http='h11')
    server = uvicorn.Server(cfg)
    threading.Thread(target=server.run, daemon=True, name='dv-web').start()
    return server


def _wait_ready(port, timeout=15):
    """对本机环回端口做 TCP 探活，确认服务已监听。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def run(browser=False, port=0):
    database.init()
    port = port or _free_port()
    server = _start_server(port)
    if not _wait_ready(port):
        print('server failed to start', flush=True)
        return
    url = f'http://127.0.0.1:{port}/'

    if not browser:
        try:
            import webview  # pywebview
            webview.create_window('DocVault', url, width=1360, height=900,
                                  min_size=(960, 640))
            webview.start()  # 阻塞至窗口关闭
            server.should_exit = True
            return
        except Exception as e:
            print(f'webview unavailable ({e!r}), fallback to browser', flush=True)

    webbrowser.open(url)
    print(f'DocVault running at {url}  (Ctrl+C 退出)', flush=True)
    try:
        while server.is_alive():
            time.sleep(0.5)
    except KeyboardInterrupt:
        server.should_exit = True


if __name__ == '__main__':
    run()
