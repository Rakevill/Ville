"""Единственный экземпляр приложения + IPC для показа окна.

Mutex гарантирует, что только один процесс держит приложение.
Второй запуск шлёт первому сигнал 'show' через localhost-сокет
и завершается. Первый показывает окно — пользователь видит,
что клик по exe сработал.
"""
import ctypes
import socket
import threading
import time
from ctypes import wintypes

_MUTEX_HANDLE = None
IPC_PORT = 50513
ERROR_ALREADY_EXISTS = 183

_kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
_kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
_kernel32.CreateMutexW.restype = wintypes.HANDLE
_kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
_kernel32.CloseHandle.restype = wintypes.BOOL


def acquire_single_instance(name='VilleLauncherMutex') -> bool:
    """True — мы первый, False — кто-то уже работает."""
    global _MUTEX_HANDLE
    handle = _kernel32.CreateMutexW(None, False, name)
    if not handle:
        return False
    err = ctypes.get_last_error()
    if err == ERROR_ALREADY_EXISTS:
        _kernel32.CloseHandle(handle)
        return False
    _MUTEX_HANDLE = handle
    return True


def try_activate_existing(payload='show', timeout=1.5) -> bool:
    """Послать строку уже запущенному экземпляру. True — успешно."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', IPC_PORT), timeout=0.3) as s:
                s.sendall(payload.encode('utf-8') + b'\n')
                return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.1)
    return False


def start_ipc_server(on_message) -> threading.Thread:
    """on_message(payload: str) — вызывается с содержимым сообщения."""
    def serve():
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            server.bind(('127.0.0.1', IPC_PORT))
            server.listen(5)
        except OSError:
            return
        while True:
            try:
                conn, _ = server.accept()
                with conn:
                    data = conn.recv(8192).decode('utf-8', errors='ignore').strip()
                    if data:
                        on_message(data)
            except Exception:
                pass

    t = threading.Thread(target=serve, daemon=True, name='ipc')
    t.start()
    return t

def release_single_instance():
    """Освободить мьютекс. Нужно перед перезапуском приложения,
    иначе новый процесс увидит, что экземпляр уже работает."""
    global _MUTEX_HANDLE
    if _MUTEX_HANDLE:
        _kernel32.CloseHandle(_MUTEX_HANDLE)
        _MUTEX_HANDLE = None