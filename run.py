from app.main import app




import glob

random_id = 'lbydrfmsucta'

current_sequences_list = glob.glob(f'temp/mixdown_{random_id}_*.mp3')

'-i '.join(current_sequences_list)

'-i ' + ' -i '.join(current_sequences_list)
 "ffmpeg -y -i FILE1 -i FILE2 -filter_complex '[0:0][1:0] amix=inputs=2:duration=longest' -c:a libmp3lame OUTPUTFILE"