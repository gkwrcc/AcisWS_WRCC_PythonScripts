#!/usr/bin/python

__prog__ = 'sodrun.py'
__version__ = "$Id: sodrun.py,v 1.0 2012/06/20 bdaudert Exp$"

usage = '''
        This program finds runs of SOD data at, above or below specified levels
	of precipitation, snowfall, snowdepth, max and min temperatures.
	For more information, please refer to sodrun.txt
        '''
##############################################################################
# import standard python modules
import os, sys
import optparse
##############################################################################
# import modules required by Acis
import urllib2
import json
##############################################################################
# set Acis data server
base_url = 'http://data.rcc-acis.org/'
##############################################################################
# Functions
def parse_args():
	usage = ''' %prog [options]
	'''

	parser = optparse.OptionParser( usage )

	parser.add_option('-c','--coop-station-id',action='store',type='int',\
	metavar='NUMSTA',help='Required: COOP Station number')

	parser.add_option('-s','--start-date',action='store',type='string',\
	default='por', metavar='NYRST',help='Starting year, format: 19950101, default por= period of record ')

	parser.add_option('-f','--end-date',action='store',type='string',\
	default='por', metavar='NYREN',help='Ending year, format: 20010501, default por= period of record ')

	parser.add_option('-e','--element',action='store',type='string',\
	metavar='ELMT',help='Required: Pick the element of interest: maxt, mint, snow, snwd or pcpn \
	units: maxt, mint: whole degrees, snow: tenth of inches, snwd: whole inches, pcpn: hundredths of inches')

	parser.add_option('-a','--aeb',action='store',type='string',\
	metavar='AEB',help='Required: A = above, E = equal, B = below')

	parser.add_option('-t','--threshold',action='store',type='int',\
	default=0, metavar='THR',help='Required: INTEGER threshold value. \
	NOTE: decimal pcpn, snow and snwd are converted to comparable int values')

	parser.add_option('-m','--min-run',action='store',type='int',\
	default=1, metavar='MINRUN',help='Enter streaks lasting duration (in days)')

	parser.add_option('-n','--name',action='store',type='string',\
	default=None, metavar='NAME',help='Give your run a name if you would like')

	parser.add_option('-o','--output-file',action='store',type='string',\
	default=None, metavar='OUTPUT',help='Output file name, default is screen')

	parser.add_option('-v','--version',action='store_true',default=False,\
	help='Display version information and exit')

	(opts,args) = parser.parse_args()

	if not opts.coop_station_id or not opts.start_date or not opts.end_date \
	or not opts.element or not opts.aeb:
		print >> sys.stderr, 'missing command line options; \
		try python sodrun.py --help for usage'
		sys.exit(0)

	if len(str(abs(opts.coop_station_id))) != 6 or not isinstance(opts.coop_station_id, int):
		print >> sys.stderr, 'Invalid --coop_station_id, needs to be 6 digit number'
		sys.exit(0)

	if opts.start_date == 'por' or opts.end_date == 'por':
		pass
	else:
		if len(opts.start_date) != 8 or len(opts.end_date) != 8:
			print >> sys.stderr, '--start-date and --end-date need to be given in \
			8 digits, format 20010130'
			sys.exit(0)

	if opts.element not in ['mint', 'maxt', 'pcpn', 'snow', 'snwd']:
		print >> sys.stderr, '--element needs to be one of mint, maxt, prcp, snow, snwd; \
		try python sodrun.py --help for usage'
		sys.exit(0)

	if opts.aeb not in ['A', 'B', 'E']:
		print >> sys.stderr, '--aeb needs to be A,B or E; try python sodrun.py --help for usage'
		sys.exit(0)

	return opts, args

#Acis WebServices functions
##########################
def make_request(url,params) :
	req = urllib2.Request(url,
	json.dumps(params),
	{'Content-Type':'application/json'})
	response = urllib2.urlopen(req)
	return json.loads(response.read())

def MultiStnData(params) :
	return make_request(base_url+'MultiStnData',params)

def StnData(params) :
	return make_request(base_url+'StnData',params)

#Function utilized to check for gap in data
###########################################
def JulDay(year, mon, day):
	jd = 367 * year - 7 * (year + (mon + 9) / 12) / 4\
	- 3 * ((year + (mon - 9) / 7) / 100 +1) / 4\
	+ 275 * mon / 9 + day + 1721029

	jd+=1
	return int(jd)

#Routine to convert data from format 1972-08-04 to 19720804 (str)
#################################################################
def convert_date(date):
	str_date = ''.join(date.split('-'))
	return str_date

#Routines returning output strings
##################################
def write_str_missing(days, nxt):
        print_str = str(days) + ' DAYS MISSING ' + ' NEXT DATE : ' + str(nxt)
        return print_str

def write_str_data(start, end, days, el):
        print_str = el + ' ' + op + ' ' + str(opts.threshold)  + ' START : ' + str(start) \
                                + ' END : ' + str(end) + ' ' + str(days) + ' DAYS'
        return print_str

def write_str_thresh(days, nxt):
	print_str = str(days) + ' DAYS WHERE THRESHOLD NOT MET ' + ' NEXT DATE : ' + str(nxt)
        return print_str


#Routine to print results to screen or write to file
####################################################
def write_or_print(string, pr_flag):
	if pr_flag == 'W':
		if not f:
			print >> sys.stderr, 'Cannot find file to write to!'
			sys.exit(1)
		string = string + '\n'
		f.write(string)
	elif pr_flag == 'P':
		print string
	else:
		print >> sys.stderr, 'Invalid print flag, need P (print to screen) or W (write to file) !'
		sys.exit(1)

#Routine to update run_cnt dict
###############################
def update_run_cnt(run_cnt, day_cnt):
	if day_cnt in run_cnt:
		run_cnt[day_cnt]+=1
	else:
		run_cnt[day_cnt]=1

#Routine to convert data to integer to avoid floating point errors
#NOTE: date_val[1] is unicode and does not support arithmetic directly,
#int(date_val[1]) is not valid, FIX ME: ask Greg or Grant about unicode
def convert_to_int(element, val):
	if element in ['maxt', 'mint', 'snwd']:
		data = int(float(val))
	elif element == 'snow':
		data = int(float(val) * 10)
	elif element == 'pcpn':
		data = int(float(val) * 100)
	return data

#Routine to convert integer threshold value to float if needed:
def convert_to_float(element, val):
        if element in ['maxt', 'mint', 'snwd']:
                data = int(float(val))
        elif element == 'snow':
                data = val / 10.0
        elif element == 'pcpn':
                data = val / 100.0
        return data


#Main function to compute days and run length for given input values
####################################################################
def compute_runs(in_data, aeb, op, el, threshold, jd_start, jd_end, f=None):
	day_cnt = 0
	run_cnt = {} #run_cnt[day] = # of runs
	flag = 0 #flag are 'M', 'S', 'A', 'T' (GHCN flags) or 'D', '0'(internal flag)
	run_start = 0
	run_end = 0
	days_missing = 0
	days_not_thresh = 0
	gap = False

	if f:
		pr_flag = 'W'
	else:
		pr_flag = 'P'

	#Loop over [date, value] pairs of input data
	############################################
	for i, date_val in enumerate(in_data):

		#Compute Julian day for current data and check for gap with previous data
		#########################################################################
		if i == 0:
			jd_old = jd_start
		else:
			jd_old = jd
		date_split = date_val[0].split('-')
		jd = JulDay(int(date_split[0]), int(date_split[1]), int(date_split[2]))
		gap_days = jd - jd_old
		if i == 0 and gap_days >0: #found gap between user given start data and  first data point
			print_str =  write_str_missing(str(gap_days), convert_date(date_val[0]))
			write_or_print(print_str, pr_flag)
		elif gap_days >1: #gap between two successive data entries
			days_missing += gap_days
			gap = True
		else:
			gap = False

		#Take care of gaps in data
		######################################################
		if gap and day_cnt !=0: # we are in middle of run and need to stop it
			run_end = in_data[i-1][0]
			if day_cnt >= opts.min_run:
				update_run_cnt(run_cnt, day_cnt)
				print_str1 = write_str_data(convert_date(run_start), convert_date(run_end), str(day_cnt), el)
				write_or_print(print_str1, pr_flag)
				if days_missing !=0:
					print_str2 = write_str_missing(str(days_missing), convert_date(date_val[0]))
					write_or_print(print_str2, pr_flag)
			day_cnt = 0
			flag = 0
			days_missing = 0
		elif gap and days_missing !=0:
			days_missing+=gap
		elif gap and days_not_thresh !=0:
			print_str = write_str_thresh(str(days_not_thresh), convert_date(date_val[0]))
			write_or_print(print_str, pr_flag)


		#Check internal flags
		#####################
		if flag == 0 and day_cnt == 0: #Beginning of a run
			run_start = date_val[0]
			#check for missing days
			if days_missing != 0:
				flag = date_val[1][-1]
				if not flag in ['M', 'S', 'A', 'T', ' ']:
					print_str = write_str_missing(str(days_missing), convert_date(date_val[0]))
					write_or_print(print_str, pr_flag)
					days_missing = 0
		elif flag == 0 and day_cnt != 0: #Middle of run
			day_cnt+=1
			continue

		elif flag == 'D' and day_cnt != 0: #End of run
			if day_cnt >= opts.min_run:
				update_run_cnt(run_cnt, day_cnt)
				print_str = write_str_data(convert_date(run_start), convert_date(run_end), str(day_cnt), el)
				write_or_print(print_str, pr_flag)
			day_cnt = 0
			flag = 0


		#Check data flags
		##############################
		flag = date_val[1][-1]
		if flag in ['T', 'A', 'S', 'M', ' ']:
			if flag in ['M', ' ']:
				days_missing+=1
			if day_cnt != 0 and day_cnt >= opts.min_run: #Run ends here
				run_end = date_val[0]
				update_run_cnt(run_cnt, day_cnt)
				print_str = write_str_data(convert_date(run_start), convert_date(run_end), str(day_cnt), el)
				write_or_print(print_str, pr_flag)
			if days_not_thresh != 0:
				print_str = write_str_thresh(str(days_not_thresh), convert_date(date_val[0]))
				write_or_print(print_str, pr_flag)
				days_not_thresh = 0
			if flag in ['T', 'A', 'S']:
				days_not_thresh+=1
			day_cnt = 0
			continue

		#Check for invalid flag
		#######################
		if not flag.isdigit():
			print >> sys.stderr, 'found invalid flag %s' % str(flag)
			sys.exit(1)

		#Make sure data can be converted to float
		#########################################
		try:
			float(date_val[1])
		except ValueError:
			print >> sys.stderr, '%s cannot be converted to float' % str(date_val[1])
			sys.exit(1)

		#Data is sound and we can check threshold condition
		###################################################
		data = convert_to_int(opts.element, date_val[1])

		if (aeb == 'A' and data > threshold) or (aeb == 'B' and data < threshold) \
		or (aeb == 'E' and data == threshold):
			if day_cnt == 0: #Start of run
				run_start = date_val[0]
				if days_missing != 0:
					print_str = write_str_missing(str(days_missing), convert_date(date_val[0]))
					write_or_print(print_str, pr_flag)
					days_missing = 0
				if days_not_thresh != 0:
                                	print_str = write_str_thresh(str(days_not_thresh), convert_date(date_val[0]))
                                	write_or_print(print_str, pr_flag)
                                	days_not_thresh = 0
			day_cnt+=1
		else: #Run ends here
			days_not_thresh+=1
			run_end = date_val[0]

			flag = 'D'
	#Check if we are in middle of run at end of data
	################################################
	if flag == 0 or flag.isdigit(): #last value is good
		if day_cnt !=0 and day_cnt >= opts.min_run:
			update_run_cnt(run_cnt, day_cnt)
                        print_str = write_str_data(convert_date(run_start), convert_date(run_end), str(day_cnt), el)
                        write_or_print(print_str, pr_flag)
		elif days_missing != 0:
			print_str = write_str_missing(str(days_missing), convert_date(date_val[0]))
			write_or_print(print_str, pr_flag)
		elif days_not_thresh != 0:
			print_str = write_str_thresh(str(days_not_thresh), convert_date(date_val[0]))
			write_or_print(print_str, pr_flag)
	elif flag == 'M': #last value is mising
		if days_not_thresh != 0:
			print_str = write_str_thresh(str(days_not_thresh), convert_date(date_val[0]))
			write_or_print(print_str, pr_flag)
	elif flag == 'D': #last value is below threshold
		if day_cnt !=0 and day_cnt >= opts.min_run:
			update_run_cnt(run_cnt, day_cnt)
			print_str = write_str_data(convert_date(run_start), convert_date(run_end), str(day_cnt), el)
			write_or_print(print_str, pr_flag)
		if days_not_thresh != 0:
			print_str = write_str_thresh(str(days_not_thresh), convert_date(date_val[0]))
			write_or_print(print_str, pr_flag)

	#Check for gap between last data point and run_end given by user
	#################################################################
	if jd_end - jd >0:
		days_missing+= jd_end - jd

	if days_missing != 0:
		print_str = write_str_missing(str(days_missing), convert_date(in_data[-1][0]))
		write_or_print(print_str, pr_flag)

	return run_cnt



##############################################################################
# MAIN

opts, args = parse_args()

#Set up parameters for data request
params = dict(sid='%s' % opts.coop_station_id,sdate='%s' % opts.start_date, edate='%s' \
	% opts.end_date, elems='%s' % opts.element)

#Retrieve data via Acis webservices
request = StnData(params)

try:
	request['meta']
except:
	if request['error']:
		print >> sys.stderr, '%s' % str(request['error'])
	else:
		print >> sys.stderr, 'Unknown error ocurred. Check input values!'
	sys.exit(1)

try:
	request['data']
except:
	print >> sys.stderr, 'No data found! Check your dates!'
	sys.exit(1)

#Request['data'] is a list of [date, value] pairs
data = request['data']
print data

#Convert input data to Julian days and check that end_date later than start_date
if opts.start_date != 'por':
	s_date = params['sdate']
        jd_start = JulDay(int(opts.start_date[:4]), int(opts.start_date[4:6]), int(opts.start_date[6:8]))
else:
	s_date = convert_date(data[0][0])
	date_split = data[0][0].split('-')
	jd_start = JulDay(int(date_split[0]), int(date_split[1]), int(date_split[2]))

if opts.end_date != 'por':
	e_date = params['edate']
        jd_end = JulDay(int(opts.end_date[:4]), int(opts.end_date[4:6]), int(opts.end_date[6:8]))
else:
	e_date = convert_date(data[-1][0])
	date_split = data[-1][0].split('-')
        jd_end = JulDay(int(date_split[0]), int(date_split[1]), int(date_split[2]))
if jd_start >= jd_end:
        print >> sys.stderr, 'Invalid start/end dates; end_date should be later than start_date!'
        sys.exit(0)



#Write and print header conforming to Kelly's output format
if opts.aeb == 'A':
	op = '>'
elif opts.aeb == 'B':
	op = '<'
else:
	op = '='

if opts.element == 'pcpn':
	el = 'PCPC'
elif opts.element == 'snow':
	el = 'SNFL'
elif opts.element == 'snwd':
	el = 'SNDP'
elif opts.element == 'maxt':
        el = 'TMAX'
elif opts.element == 'mint':
        el = 'TMIN'


thresh = str(convert_to_float(opts.element, opts.threshold))

print_str =  \
' STATION : COOP_STATION_ID : ' + params['sid'] +  ' NAME : '\
+ str(request['meta']['name']) + ' STATE : ' + str(request['meta']['state']) \
+ '\n' + ' RUNS OF ' + el + ' ' + op + '\n' + ' START: ' + s_date + ' END: ' + \
e_date + '\n' + ' MINIMUM DURATION ' + str(opts.min_run) + '\n'

if opts.output_file:
	f = open(opts.output_file, 'w')
	f.write(print_str)
	f.close()
else:
	print print_str

#Run analysis
if opts.output_file:
	f = open(opts.output_file, 'a')
	run_cnt = compute_runs(data, opts.aeb, op, el, opts.threshold, jd_start, jd_end, f)
else:
	run_cnt = compute_runs(data, opts.aeb, op, el, opts.threshold, jd_start, jd_end)

#Print summary of results
if opts.output_file:
	f.write('DAYS NUMBER_OF_RUNS \n')
else:
	print 'DAYS NUMBER_OF_RUNS'

key_list =  sorted(run_cnt)
key_list.sort()

for key in key_list:
	if opts.output_file:
		f.write('%s \t %s \n' % (key, run_cnt[key]))
	else:
		print '%s \t %s' % (key, run_cnt[key])

if opts.output_file:
	f.close()
