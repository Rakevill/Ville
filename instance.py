"""Один экземпляр приложения на пользователя.

CreateMutexW с уникальным именем: если мьютекс уже существует
(ERROR_ALREADY_EXISTS = 183), значит, предыдущий экземпляр жив.
"""
import ctypes

_MUTEX_HANDLE = None  # держим ссылку, чтобы Windows не освободила мьютекс


def acquire_single_instance(name='VilleLauncher') -> bool:
    global _MUTEX_HANDLE
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.CreateMutexW(None, True, name)
    err = kernel32.GetLastError()
    if err == 183:                       # ERROR_ALREADY_EXISTS
        if handle:
            kernel32.CloseHandle(handle)
        return False
    _MUTEX_HANDLE = handle
    return True