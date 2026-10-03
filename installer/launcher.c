// KoeType.app の実行ファイル。Python本体を子プロセスとして起動する。
// 子プロセスにすることで、マイク・入力監視などの許可が「KoeType」に紐づく。
#include <signal.h>
#include <spawn.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>

extern char **environ;
static pid_t child = 0;

static void forward(int sig) {
    if (child > 0) kill(child, sig);
}

int main(void) {
    if (chdir(KOETYPE_DIR) != 0) { perror("chdir"); return 1; }
    char *argv[] = {KOETYPE_DIR "/.venv/bin/python", "-u", "-m", "koetype", NULL};
    signal(SIGTERM, forward);
    signal(SIGINT, forward);
    signal(SIGHUP, forward);
    if (posix_spawn(&child, argv[0], NULL, NULL, argv, environ) != 0) { perror("spawn"); return 1; }
    int status = 0;
    while (waitpid(child, &status, 0) < 0) {}
    return WIFEXITED(status) ? WEXITSTATUS(status) : 1;
}
