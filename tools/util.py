import subprocess

def run_cmd_out(cmd: str) -> subprocess.CompletedProcess:
    """
    Run the specified command, returning the output of the command
    """
    res = subprocess.run(cmd.split(" "), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    res.stdout = res.stdout.decode("utf-8", "replace")
    res.stderr = res.stderr.decode("utf-8", "replace")
    return res


def run_cmd(cmd: str) -> bool:
    """
    Run the specified command, returning True/False
    """
    res = run_cmd_out(cmd)
    if res.returncode != 0:
        print(res.stderr)
        return False
    return True
