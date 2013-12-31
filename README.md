tri
===

subleq compiler/interpreter

### usage


	# compile to subleq binary
	python asm.py example/fibb.src`

	# run
	python run.py example/fibb.out


### simple example (2+2=4)

	  jmp start;
	
	a: mem ?;
	b: mem 2;
	c: mem 2;

	start: 
	  mov a constadr(0);
	  add a b;
	  add a c;
	  out a;


### instruction set

	tri x y z;     *x -= *y; if (*x <= 0) goto z;


### syntaxtic sugar

	jmp z;         goto z;
	sub x y;       *x -= *y;
	mov x y;       *x = *y;
	out x;         printf("%i", *x);
	add x y;       *x += *y;
	jle x y z;     if (*x <= *y) goto z;
	nil;           goto next; next:
	mem x1 x2 ..;  // init memory from here to x1, x2, ..


### addressing

	14             direct/address to memory cell number '14'
	start          by label/address to memory cell labeled 'start'
	constadr(3)    to value/address to memory cell containing value '3'
	next()         next cell/address to memory cell immiediatly afterwards current cell


### self-modifying/indirect addressing example

	  jmp start;

	data: mem 1 2 3 4 5;
	 len: mem 5;
	   i: mem 1;

	start:
	  copy_to: mem outadr(); copy_from: mem data; mem next();
	  add copy_from constadr(1);
	  add i constadr(1);
	  jle i len start;
  
  





