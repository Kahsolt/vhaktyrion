all: printer

printer:
	python printer.py
	
clean:
	rm -rf .*log *.o

clean_fontcache:
	rm -rf fonts.pkl