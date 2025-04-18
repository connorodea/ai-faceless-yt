run:
	python main.py

clean:
	rm -rf temp/*.png logs/*.log music_*.mp3

test:
	pytest tests/