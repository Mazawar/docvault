"""任务服务：串行队列 + jobs 表持久化（同步/导出等重活单信号量排队）。"""
import queue
import threading
import time
import traceback
from ..models import repository

_q: queue.Queue = queue.Queue()
_worker_started = False
_start_lock = threading.Lock()


def _worker():
    while True:
        jid, fn = _q.get()
        log = []

        def logcb(m):
            log.append(str(m))
            repository.job_save(jid, 'running', log[-200:])

        try:
            repository.job_save(jid, 'running', log)
            fn(logcb)
            repository.job_save(jid, 'done', log, time.strftime('%H:%M:%S'))
        except Exception as e:
            logcb('ERROR: ' + repr(e)[:800])
            logcb(traceback.format_exc()[-1500:])
            repository.job_save(jid, 'error', log, time.strftime('%H:%M:%S'))
        finally:
            repository.prune_jobs()


def _ensure_worker():
    global _worker_started
    with _start_lock:
        if not _worker_started:
            threading.Thread(target=_worker, daemon=True, name='dv-jobs').start()
            _worker_started = True


def start_job(name, fn):
    """入队一个任务并立即返回 job id。fn 接收 logcb(message) 回调。"""
    _ensure_worker()
    jid = repository.job_add(name)
    _q.put((jid, fn))
    return jid
