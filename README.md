# Tetris
## How to use the lib
- Make sure you have `gcc` installed
- Compile using `make`
- Afterwards use `LD_PRELOAD=is_it_openmp.so APP`

## How to generate the plots
1. Set up a Python venv `python3 -m venv venv`
2. Activate it `source venv/bin/activate`
3. Install dependencies `pip install matplotlib colorama`
4. Run `python3 extractor.py --help`
