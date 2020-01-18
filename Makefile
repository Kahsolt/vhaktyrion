.PHONY : w clean

writer:
	python writer.py

clean:
	rm -rf fonts/*.pkl
