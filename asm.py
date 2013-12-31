# coding: utf-8
from collections import defaultdict
from functools import partial
from pyparsing import Word, alphas, nums, Literal, Forward, Optional, Keyword, StringEnd
import pyparsing
import struct
import sys
import os
import traceback

def List(item):
	body = Forward()
	body << (item + Optional(body))
	return Optional(body)

class Token(object):
	def __init__(self, name, s, loc, ts):
		super(Token, self).__init__()
		self.s = s
		self.loc = loc
		self.ts = ts
		self.type = name
		
	def line_no(self):
		return pyparsing.line_no(loc, s)
		
	def __repr__(self):
		return '{}({})'.format(self.type, ','.join(map(repr, self.ts)))

	def __getitem__(self, i):
		return self.ts[i]

	def __iter__(self):
		return iter(self.ts)


def tokenize(name):
	def inner(s,l,ts):
		try:		
			t = Token(name, s,l,ts)
			# print 'tokenizing', name, t.line_no()
			#t.add_loc_info(s, l, name)
			return [t]
		except:
			print traceback.format_exc()
			raise Exception()

	return inner

def map_int(s,l,ts):
	assert len(ts) == 1
	return [int(ts[0])]

def run(func):
	def inner(s,l,ts):
		try:

			if len(ts) == 1 and type(ts[0]) is Token:
				ts = ts[0].ts

			func(*ts)
		except:
			print traceback.format_exc()
			raise Exception('uhy')

	return inner


class TokenFact(object):
	def __getattr__(self, name):
		return lambda *args: Token(name, None, None, args)

t = TokenFact()



class BindInfo(object):
	def __init__(self, adr=-1, defined=False):
		self.adr = adr
		self.defined = defined
		
	def __iter__(self):
		yield adr
		yield defined



class Gen(object):
	def err(loc, *msg):
		if isinstance(loc, tuple):
			line_no, pos_no = loc
		else:
			line_no, pos_no = loc, '?'
			
		self.loc = (line_no, pos_no)
		

	def __init__(self):
		self.cpos = 0
		self.code = []
			
		self.instr = {
			'tri': self.gen_tri,  # subleq
			'jmp': self.gen_jmp,
			'sub': self.gen_sub,
			'mov': self.gen_mov,
			'out': self.gen_out,
			'add': self.gen_add,
			'jle': self.gen_jle,
			'nil': self.gen_nil,
			'mem': self.gen_mem,
		}		
		
		self.func = {
			'tmpadr': self.gen_temp_ref,
			'constadr': self.gen_const_ref,
			'outadr': self.gen_output_ref,
			'endadr': self.gen_end_ref,
			'next': self.gen_next_ref,  # volatile!
		}
			
		self.labeldef = defaultdict(lambda: BindInfo())		
		self.constdef = defaultdict(lambda: BindInfo())
		self.tempdef = defaultdict(lambda: BindInfo())
		
		self.ident = set(self.instr.keys() + self.labeldef.keys() + self.func.keys())
		
		self.parser = self.make_parser()
		

	def reg_name(self, name):
		if name in self.ident:
			raise Exception("identifier '{}': already defined".format(name))
		else:
			self.ident.add(name)
	

	def gen_code(self, n):	
		assert type(n) is int
		self.code.append(n)
		self.cpos += 1
	
	def gen_number(self, n):
		assert type(n) is int
		self.gen_code(n)
		
	def gen_arg(self, arg):
		""" gen instruction argument """
		
		if type(arg) is int:
			self.gen_number(arg)
			
		elif arg.type == 'LabelRef':
			self.gen_label_ref(*arg)
			
		elif arg.type == 'LabelGen':
			self.gen_label_gen(*arg)
			
		else:
			raise Exception("unexpected error")


	""" SIMPLE FUNC """
		
	def gen_next_ref(self):
		self.gen_code(self.cpos+1)
						
	def gen_end_ref(self):
		self.gen_code(-1)

	def gen_output_ref(self):
		self.gen_code(-2)
	
	def gen_label_gen(self, ident, *args):
		if ident in self.func:
			self.func[ident](*args)	
		else:
			raise Exception("invalid function name")


		
	""" GENERIC BIND """
			
	def gen_bind_def(self, bind):	
		if bind.defined:
			raise Exception('bind already defined')
		
		# update deferred binds
		i = bind.adr
		while i != -1:			
			j = self.code[i]
			self.code[i] = self.cpos
			i = j
			
		# define			
		bind.adr = self.cpos
		bind.defined = True
				
	def gen_bind_ref(self, bind):
		if not bind.defined:
			# deferred bind
			prev = bind.adr
			bind.adr = self.cpos    # update llhead
			self.gen_code(prev)
		else:
			# normal bind
			self.gen_code(bind.adr)

	""" LABEL """

	def gen_label_ref(self, ident):
		self.gen_bind_ref(self.labeldef[ident])
	
	
	def gen_label_def(self, ident):
		self.reg_name(ident)		
		self.gen_bind_def(self.labeldef[ident])

	""" CONST """
	
	def gen_const_ref(self, N):
		assert type(N) is int				
		self.gen_bind_ref(self.constdef[N])
		
	def gen_const_space(self):
		for N in sorted(self.constdef.keys()):
			# define bind
			self.gen_bind_def(self.constdef[N])
						
			# gen const			
			self.gen_code(N)

	""" TEMP """
	
	def gen_temp_ref(self, i):
		assert type(i) is int
		self.gen_bind_ref(self.tempdef[i])
			
	def gen_temp_space(self):
		for N in sorted(self.tempdef.keys()):
			# define bind
			self.gen_bind_def(self.tempdef[N])
						
			# gen ?	
			self.gen_code(0)
	
	""" INSTR """		
	
	def gen_instr(self, ident, *args):		
		if ident in self.instr:
			self.instr[ident](*args)
		else:
			raise Exception("instruction '{}': unrecognized".format(ident))
		
	def gen_tri(self, X, Y, Z):
		self.gen_arg(X); self.gen_arg(Y); self.gen_arg(Z)
		
	def gen_jmp(self, Z):
		cst = partial(t.LabelGen, 'constadr')
		self.gen_tri(cst(0), cst(0), Z);
		
	def gen_sub(self, X, Y):
		self.gen_tri(X, Y, t.LabelGen('next'))
		
	def gen_mem(self, *xs):
		for x in xs:
			self.gen_arg(x)
		
	def gen_mov(self, X, Y):
		next = t.LabelGen('next')
		T = t.LabelGen('tmpadr', 0)
		self.gen_arg(X); self.gen_arg(X); self.gen_arg(next)
		self.gen_arg(T); self.gen_arg(T); self.gen_arg(next)
		self.gen_arg(T); self.gen_arg(Y); self.gen_arg(next)
		self.gen_arg(X); self.gen_arg(T); self.gen_arg(next)

	def gen_out(self, X):
		self.gen_tri(t.LabelGen('outadr'), X, t.LabelGen('next'))

	def gen_add(self, X, Y):
		T = t.LabelGen('tmpadr', 0)
		next = t.LabelGen('next')		
		self.gen_tri(T, T, next)
		self.gen_tri(T, Y, next)
		self.gen_tri(X, T, next)
		
	def gen_jle(self, X,Y,Z):
		T = t.LabelGen('tmpadr', 0)
		A = t.LabelGen('tmpadr', 1)
		next = t.LabelGen('next')		
		# mov
		self.gen_tri(A,A,next)
		self.gen_tri(T,T,next)	
		self.gen_tri(T,X,next)
		self.gen_tri(A,T,next)		
		# subleq
		self.gen_tri(A,Y,Z)

	def gen_nil(self):
		cst = partial(t.LabelGen, 'constadr')
		next = t.LabelGen('next')		
		self.gen_tri(cst(0), cst(0), next)
		
	def gen_jmp_end(self):
		cst = partial(t.LabelGen, 'constadr')
		self.gen_tri(cst(0), cst(0), -1)

	def gen_end_progr(self, *instrs):
		self.gen_jmp_end()
		self.gen_const_space()
		self.gen_temp_space()
		
		
	def make_parser(self):
		g = self
		
		lpar = Literal('(').suppress()
		rpar = Literal(')').suppress()
		colon = Literal(':').suppress()
		delimiter = Literal(';').suppress()
		unknown = Literal('?').setParseAction(lambda s,l,t: [0])  # ? -> number 0
		
		number = Word(nums).setParseAction(map_int)

		ident = Word(alphas+'_', alphas+nums+'_')

		label_gen = (
			ident + lpar + Optional(number) + rpar
		).setParseAction(tokenize('LabelGen'))

		label_def = (ident + colon).setParseAction(tokenize('LabelDef'), run(g.gen_label_def))

		label_ref = ident.copy().setParseAction(tokenize('LabelRef'))

		operand = number | label_gen | label_ref | unknown

		instr = (ident + List(operand) + delimiter).setParseAction(tokenize('Instr'), run(g.gen_instr))
		
		entry = instr | label_def

		progr = List(entry).setParseAction(run(self.gen_end_progr))
		
		return progr
		

	def parse_file(self, f):
		x = self.parser.parseFile(f, parseAll=True)
		return self.code
		
	def parse_string(self, text):
		x = self.parser.parseString(text, parseAll=True)
		return self.code



def main():
	
	fname = sys.argv[1]
	text = open(fname, 'r').read()
	
	rs = Gen().parse_string(text)
	oname = os.path.splitext(fname)[0] + '.out'
	
	with open(oname, 'wb') as f:
		for rr in rs:
			f.write(struct.pack('i', rr))
	
def test():
	def compile_asm(src):
		return Gen().parse_string(src)

	r = compile_asm('''
		main: tri 1 2 3;
	''')
	assert r == [1,2,3, 6,6,-1, 0], repr(r)

	r = compile_asm('''
		tri 1 2 3; tri 4 5 6;
	''')
	assert r == [1,2,3, 4,5,6, 9,9,-1, 0], repr(r)

	r = compile_asm('''
		tri 0 label 2; label:
	''')
	assert r == [0,3,2, 6,6,-1, 0], repr(r)

	r = compile_asm('''
		tri label label label; label:
	''')
	assert r == [3,3,3, 6,6,-1, 0], repr(r)
	
	r = compile_asm('''
		label: tri label label label;
	''')
	assert r == [0,0,0, 6,6,-1, 0], repr(r)

	r = compile_asm('''
		label1:label2:
	''')
	assert r == [3,3,-1, 0], repr(r)

	r = compile_asm('''
		jmp 8;
	''')
	assert r == [6,6,8, 6,6,-1, 0], repr(r)
	
	r = compile_asm('''
		tri 0 constadr(5) 0; tri 0 constadr(5) 0;
	''')
	assert r == [0,10,0,  0,10,0,  9,9,-1,  0, 5], repr(r)


if __name__ == '__main__':
	main()
	
	
	
	
	

