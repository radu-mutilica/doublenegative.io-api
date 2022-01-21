# doublenegative.io-api
Python API Wrapper for doublenegative.io
## What is it?
Use this tool to convert your mp3 music library to high quality flac format, downloaded from 
https://doublenegative.io. Currently, only the `deezer` backend is supported, but you are free to 
implement others, like tidal.
## Usage
- Open up `bin/config.yaml`
- Under the path section change `mp3_library` and `flac_library`
- Run `bin/doublenegative-api.py`
- At the end of the run, a log will be generated containing the tracks it failed to convert to flac.
## Note
It is assumed that your `mp3_library` is under the following folder structure:
```
music
    \ genre1
    |       \ song1
    |         song2
    |         song3
    \ genre2
    |       \ song4
    |         song5
    \ genre3
            \ song6
              song7
```
Will probably work without this `genre` structure, but have not tested it.
Make sure your mp3s are named following this format:
```
<artist> [feat.|,|&] <another artist> - <song name> (<third artist> remix)
<artist> [feat.|,|&] <another artist> - <song name> (extended/original/club mix)
```
## Todo
- Add album art
- Add id3 tags
- Improve failure logs
- Add retries for failures with variations of the track name