CC = gcc
CFLAGS = -g -Wall -O3 -Wunused-variable # -Wconversion
#CFLAGS = -g3 -Wall -O0
INCLUDES = -I../linux/usr/include
LIBS = -lm -lpthread

src=$(wildcard *.c)
deps=$(wildcard *.h)
obj=$(patsubst %.c,%.o,$(src))

target = gups-pebs gups-random gups-hotset-move

all : $(target)

gups-pebs : gups.o timer.o gups-syscall.o
	$(CC) $(CFLAGS) $(INCLUDES) $^ -o $@ $(LIBS)

gups-random : gups-random.o timer.o
	$(CC) $(CFLAGS) $(INCLUDES) $^ -o $@ $(LIBS)

gups-hotset-move : gups-hotset-move.o timer.o
	$(CC) $(CFLAGS) $(INCLUDES) $^ -o $@ $(LIBS)

%.o : %.c $(deps)
	$(CC) $(CFLAGS) $(INCLUDES) -c $< -o $@ -Wall

.PHONY : clean
clean :
	$(RM) *.o $(target)
