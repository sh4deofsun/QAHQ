from enum import Enum


class Perm(str, Enum):
    WORKER_VIEW = "worker:view"
    WORKER_MANAGE = "worker:manage"
    TASK_VIEW = "task:view"
    TASK_CREATE_ROBOT = "task:create_robot"
    TASK_CREATE_COMMAND = "task:create_command"
    RESULT_VIEW = "result:view"
    RESULT_UPLOAD = "result:upload"
    USER_MANAGE = "user:manage"
    ROLE_MANAGE = "role:manage"


# Role presets created by the seeder. Admin always gets every permission.
DEFAULT_QA_PERMS = [
    Perm.WORKER_VIEW,
    Perm.TASK_VIEW,
    Perm.TASK_CREATE_ROBOT,
    Perm.RESULT_VIEW,
    Perm.RESULT_UPLOAD,
]
