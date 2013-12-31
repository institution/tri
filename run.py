import sys
import struct

def main():
	pc = 0

	fname = sys.argv[1]

	xs = []
	with open(fname, 'rb') as f:
		di = struct.calcsize('i')
		while 1:
			buf = f.read(di)
			if not buf:
				break
			xs.extend(struct.unpack('i', buf))



	while 1:			
		#print pc
		
		x,y,z = xs[pc:pc+3]
		#print 'subleq', x,y,z, '     ',xs[x],xs[y]

	
		if x == -2:
			print 'OUT:', xs[y]
			pc += 3
			
		else:
			xs[x] -= xs[y]
	
			if xs[x] <= 0:
				pc = z
			else:
				pc += 3

		if pc == -1:
			#print 'program end'
			break




main()
