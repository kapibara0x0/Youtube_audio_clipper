import os
import sys
import argparse
import logging
import shutil
import youtube_dl
import librosa

data_dir = ".\data"
temp_dir = os.path.join(data_dir, "temp")

def logger_setter(name, level, fmt='%(asctime)s %(levelname)s:: %(message)s '):
    logger = logging.getLogger(name) # ロガーの生成
    logger.setLevel(level) # ログ出力レベルの設定
    handler = logging.StreamHandler(sys.stdout) # ハンドラの生成
    logger.addHandler(handler) # ハンドラの登録
    fmter = logging.Formatter(fmt)
    handler.setFormatter(fmter)
    return logger

if __name__ == '__main__':
    logger = logger_setter(__name__, level=logging.DEBUG)
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="URL, you want to download." , type=str)   
    parser.add_argument("--savedir", help='Wav file directory path to save. Specify the following "./data" ', type=str, default="wav_A")
    parser.add_argument("--filename", help="Wav file name to save.", default="wav_file", type=str)
    parser.add_argument("--samplerate", help="Save wav file sampling rate.", default=22050, type=int)
    parser.add_argument('--ev', help="Is voice extract", action='store_true', default=False)
    parser.add_argument('--skip', help="Is download skip", action='store_true', default=False)
    parser.add_argument('--cut', nargs=2, help="Cut the time. Set the start time and end time. The time unit is minutes(min)", metavar=('cutstart','cutend'), type=int)
    
    args = parser.parse_args()

    if args.url:
        logger.info("Download :{}".format(args.url))
    else:
        logger.critical("Need --url option.")
        exit(-1) 
    save_dir = os.path.join(data_dir, args.savedir)

    os.makedirs(save_dir, exist_ok=True)
    logger.info("Maked save dir: {}".format(save_dir))

    format_ = 'bestaudio/best'
    postprocessors_ = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'},{'key': 'FFmpegMetadata'}]
    file_name = args.filename
    file_path = os.path.join(save_dir, file_name + '.%(ext)s')
    print(args.skip)
    print(args.ev)
    if not args.skip:
        ydl_opts = {'format': format_,
                'outtmpl': file_path,
                'postprocessors': postprocessors_,
                'logger': logger}
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            ydl.download([args.url])
    
    file_path_, _ = os.path.splitext(file_path)
    file_path_src = file_path_ + ".mp3"

    # 音声ファイルのカット
    if args.cut:
        from pydub import AudioSegment
        # mp3ファイルの読み込み
        target_path = os.path.abspath(file_path_src)
        logger.debug(f"Cut target path:{target_path}")
        sound = AudioSegment.from_file(target_path, "mp3")

        start = args.cut[0] * 60 * 1000 # min
        end =  args.cut[1] * 60 * 1000 # min
        
        try: 
            cut_sound = sound[start:end]
            # 抽出した部分を出力
            cut_sound.export(target_path, format="mp3")
            logger.info("Finished Cut the data.")
        except:
            logger.warning("The time to be cut exceeds the range of the original video time. Skip the cut.")
        # Resampling and, mp3 transrate to Wav

    resample_rate = args.samplerate
    src, sample_rate = librosa.load(file_path_src)
    dst = librosa.resample(src, sample_rate, resample_rate)  #resample
    file_path_dst = os.path.join(save_dir , file_name + '.wav')
    librosa.audio.sf.write(file_path_dst, dst, resample_rate) # soundfile用にwavで保存する

    logger.info("Get and Resampled: {} :{}Hz".format(file_path_dst, sample_rate))
    
    os.remove(file_path_src)
    logger.debug("Removed: {}".format(file_path_src))

    # Extract Voice
    if args.ev:
        from spleeter.separator import Separator
        os.makedirs(temp_dir)
        
        target_path = file_path_dst# ここに抽出対象のファイルパスを記述
        tgt_dir, tgt_base = os.path.split(target_path)

        # tempフォルダに音声とBGMの分離したデータを作成
        separator_2stem = Separator('spleeter:2stems')
        separator_2stem.separate_to_file(target_path, temp_dir)

        # tempフォルダからdataフォルダに移動
        tgt_base_non_ext ,_= os.path.splitext(tgt_base) 
        src = os.path.join(temp_dir, tgt_base_non_ext, "vocals.wav")
        # 元も音声ファイルを削除後、移動
        os.path.remove(target_path)
        shutil.copy(src, target_path)
        shutil.rmtree(temp_dir)
