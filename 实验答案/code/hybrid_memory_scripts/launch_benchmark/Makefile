all : launch_syscall kill_syscall

launch_syscall : launch_syscall.c
	gcc -g launch_syscall.c -o launch_syscall

kill_syscall : kill_syscall.c
	gcc -g kill_syscall.c -o kill_syscall

clean:
	rm launch_syscall kill_syscall