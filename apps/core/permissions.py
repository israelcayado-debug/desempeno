HR = "HR"
HR_ADMIN = "HR_ADMIN"
EXEC = "EXEC"
MANAGER = "MANAGER"

def in_group(user, name: str) -> bool:
    return user.is_authenticated and user.groups.filter(name=name).exists()

def is_hr(user) -> bool:
    return in_group(user, HR) or user.is_superuser

def is_hr_admin(user) -> bool:
    return in_group(user, HR_ADMIN) or user.is_superuser

def is_exec(user) -> bool:
    return in_group(user, EXEC) or user.is_superuser

def is_manager(user) -> bool:
    return in_group(user, MANAGER) or user.is_superuser

def can_manage_employees(user) -> bool:
    return is_hr(user) or is_hr_admin(user) or is_exec(user)

def can_view_reporting(user) -> bool:
    return is_exec(user) or is_hr(user) or is_hr_admin(user)

def can_evaluate(user) -> bool:
    return is_manager(user) or is_exec(user) or is_hr(user) or is_hr_admin(user)
