# -*- coding: utf-8 -*-
"""
filename: SincronizacionLock

Escritura exclusiva en un recurso compartido

Created on 12/02/2015

@author: javier
"""
from ctypes import c_int
from multiprocessing import Array, Lock, Process

__author__ = "javier"


def proceso1(a, lock):
    lock.acquire()
    print(a[:])
    for i in range(0, 10, 2):
        a[i] = i * i
    lock.release()


def proceso2(a, lock):
    lock.acquire()
    print(a[:])
    for i in range(1, 10, 2):
        a[i] = i * i
    lock.release()


if __name__ == "__main__":
    arr = Array(c_int, 10)
    lock = Lock()
    p1 = Process(
        target=proceso1,
        args=(
            arr,
            lock,
        ),
    )
    p2 = Process(
        target=proceso2,
        args=(
            arr,
            lock,
        ),
    )
    p1.start()
    p2.start()
    p1.join()
    p2.join()

    print(arr[:])
