import functools
import re
import sys

from Levenshtein import *

cdef class SequenceMatcher:
	"""A SequenceMatcher-like class built on the top of Levenshtein"""

	def _reset_cache(self):
		self._ratio = self._distance = None
		self._opcodes = self._editops = self._matching_blocks = None

	def __init__(self, isjunk=None, seq1='', seq2=''):
		if isjunk:
			print("isjunk not NOT implemented, it will be ignored")
		self._str1, self._str2 = seq1, seq2
		self._reset_cache()

	def set_seqs(self, seq1, seq2):
		self._str1, self._str2 = seq1, seq2
		self._reset_cache()

	def set_seq1(self, seq1):
		self._str1 = seq1
		self._reset_cache()

	def set_seq2(self, seq2):
		self._str2 = seq2
		self._reset_cache()

	def get_opcodes(self):
		if not self._opcodes:
			if self._editops:
				self._opcodes = opcodes(self._editops, self._str1, self._str2)
			else:
				self._opcodes = opcodes(self._str1, self._str2)
		return self._opcodes

	def get_editops(self):
		if not self._editops:
			if self._opcodes:
				self._editops = editops(self._opcodes, self._str1, self._str2)
			else:
				self._editops = editops(self._str1, self._str2)
		return self._editops

	def get_matching_blocks(self):
		if not self._matching_blocks:
			self._matching_blocks = matching_blocks(self.get_opcodes(),
													self._str1, self._str2)
		return self._matching_blocks

	def ratio(self):
		if not self._ratio:
			self._ratio = ratio(self._str1, self._str2)
		return self._ratio

	def quick_ratio(self):
		# This is usually quick enough :o)
		if not self._ratio:
			self._ratio = ratio(self._str1, self._str2)
		return self._ratio

	def real_quick_ratio(self):
		len1, len2 = len(self._str1), len(self._str2)
		return 2.0 * min(len1, len2) / (len1 + len2)

	def distance(self):
		if not self._distance:
			self._distance = distance(self._str1, self._str2)
		return self._distance

PY3 = sys.version_info[0] == 3

bad_chars = str("").join([chr(i) for i in range(128, 256)])  # ascii dammit!
if PY3:
	translation_table = dict((ord(c), None) for c in bad_chars)
	unicode = str
	string = str

def check_for_none(func):
	@functools.wraps(func)
	def decorator(*args, **kwargs):
		if args[0] is None or args[1] is None:
			return 0
		return func(*args, **kwargs)

	return decorator

cdef str asciionly(s):
	if PY3:
		return s.translate(translation_table)
	else:
		return s.translate(None, bad_chars)

cdef str asciidammit(s):
	if type(s) is str:
		return asciionly(s)
	elif type(s) is unicode:
		return asciionly(s.encode('ascii', 'ignore'))
	else:
		return asciidammit(unicode(s))

cdef class StringProcessor(object):
	"""
	This class defines method to process strings in the most
	efficient way. Ideally all the methods below use unicode strings
	for both input and output.
	"""

	regex = re.compile(r"(?ui)\W")

	@classmethod
	def replace_non_letters_non_numbers_with_whitespace(cls, a_string):
		"""
		This function replaces any sequence of non letters and non
		numbers with a single white space.
		"""
		return cls.regex.sub(" ", a_string)

	strip = staticmethod(string.strip)
	to_lower_case = staticmethod(string.lower)
	to_upper_case = staticmethod(string.upper)

cpdef str full_process_v(str s, force_ascii=False):
	"""Process string by
		-- removing all but letters and numbers
		-- trim whitespace
		-- force to lower case
		if force_ascii == True, force convert to ascii"""

	if force_ascii:
		s = asciidammit(s)
	# Keep only Letters and Numbers (see Unicode docs).
	string_out = StringProcessor.replace_non_letters_non_numbers_with_whitespace(s)
	# Force into lowercase.
	string_out = StringProcessor.to_lower_case(string_out)
	# Remove leading and trailing whitespaces.
	string_out = StringProcessor.strip(string_out)
	return string_out

cdef str make_type_consistent(s1, s2):
	"""If both objects aren't either both string or unicode instances force them to unicode"""
	if isinstance(s1, str) and isinstance(s2, str):
		return s1, s2

	elif isinstance(s1, unicode) and isinstance(s2, unicode):
		return s1, s2

	else:
		return unicode(s1), unicode(s2)

def partial_ratio(str s1, str s2):
	""""Return the ratio of the most similar substring
	as a number between 0 and 100."""

	if s1 is None or s2 is None:
		return 0

	if s1 == s2:
		return 100

	if len(s1) == 0 or len(s2) == 0:
		return 0

	s1, s2 = make_type_consistent(s1, s2)

	if len(s1) <= len(s2):
		shorter = s1
		longer = s2
	else:
		shorter = s2
		longer = s1

	m = SequenceMatcher(None, shorter, longer)
	blocks = m.get_matching_blocks()

cdef bint validate_string(s):
	"""
	Check input has length and that length > 0

	:param s:
	:return: True if len(s) > 0 else False
	"""
	try:
		return len(s) > 0
	except TypeError:
		return False

cpdef float _token_set(str s1, str s2, partial=True, force_ascii=True, full_process=True):
	"""Find all alphanumeric tokens in each string...
		- treat them as a set
		- construct two strings of the form:
			<sorted_intersection><sorted_remainder>
		- take ratios of those two strings
		- controls for unordered partial matches"""

	if s1 is None or s2 is None:
		return 0

	if not full_process and s1 == s2:
		return 100

	cdef str p1 = full_process_v(s1, force_ascii=force_ascii) if full_process else s1
	cdef str p2 = full_process_v(s2, force_ascii=force_ascii) if full_process else s2

	if not validate_string(p1):
		return 0
	if not validate_string(p2):
		return 0

	# pull tokens
	tokens1 = set(p1.split())
	tokens2 = set(p2.split())

	intersection = tokens1.intersection(tokens2)
	diff1to2 = tokens1.difference(tokens2)
	diff2to1 = tokens2.difference(tokens1)

	cdef str sorted_sect = " ".join(sorted(intersection))
	cdef str sorted_1to2 = " ".join(sorted(diff1to2))
	cdef str sorted_2to1 = " ".join(sorted(diff2to1))

	cdef str combined_1to2 = sorted_sect + " " + sorted_1to2
	cdef str combined_2to1 = sorted_sect + " " + sorted_2to1

	# strip
	sorted_sect = sorted_sect.strip()
	combined_1to2 = combined_1to2.strip()
	combined_2to1 = combined_2to1.strip()

	if partial:
		ratio_func = partial_ratio
	else:
		ratio_func = ratio

	pairwise = [
		ratio_func(sorted_sect, combined_1to2),
		ratio_func(sorted_sect, combined_2to1),
		ratio_func(combined_1to2, combined_2to1)
	]
	return max(pairwise)

cdef float token_set_ratio(str s1, str s2, force_ascii=True, full_process=True):
	return _token_set(s1, s2, partial=False, force_ascii=force_ascii, full_process=full_process)

cdef float partial_token_set_ratio(str s1, str s2, force_ascii=True, full_process=True):
	return _token_set(s1, s2, partial=True, force_ascii=force_ascii, full_process=full_process)

cdef float sort_sim(val):
	return val[0]

cdef list multi(item_, str name):
	return [token_set_ratio(item_['UniqueName'].lower(), name.lower()), item_, None]

cdef list multi2(item_, str name):
	return [token_set_ratio(item_[0], name.lower()), item_[1], None]

cpdef list item_search(str name, list reduced_ls, list id_list, list full_dict):
	"""
	Improved search with better accuracy at the cost of speed,
	To reduce the speed cost multiple async tasks are used.
	:param full_dict:
	:param id_list:
	:param name:
	:param reduced_ls:
	:return:
	"""

	cdef list ls_r = []
	cdef dict item_v3
	cdef list rating = []
	cdef dict term
	cdef list list_v2 = []
	cdef dict item_v2
	cdef str language
	cdef list rating2 = []
	cdef list term_v2

	if name in id_list:
		for item_v3 in full_dict:
			if item_v3['UniqueName'] == name:
				ls_r.append((11, item_v3))
		return ls_r

	else:
		for term in reduced_ls:
			rating.append(multi(term, name=name))

		for item_v2 in reduced_ls:
			for language in item_v2['LocalizedNames']:
				list_v2.append([item_v2['LocalizedNames'][language].lower(), item_v2])

		for term_v2 in list_v2:
			rating2.append(multi2(term_v2, name=name))

		for item in rating2:
			rating.append(item)

		rating.sort(key=sort_sim, reverse=True)
		most_likely_lang = rating[0][2]

		for nolang in [x for x in rating if x[2] is None]:
			nolang[2] = most_likely_lang
		return rating[0:5]
