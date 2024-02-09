import struct
import sys
import os
from typing import BinaryIO
from glob import glob

difficulty_array = [
    'N/A',
    'Easy',
    'Normal',
    'Hard',
    'LOGIC?!',
    'Tasukete'
]


def clear():
    os.system('cls' if os.name == 'nt' else 'clear')


def read_as_int(file, byte_amount: int):
    return int.from_bytes(file.read(byte_amount), byteorder=sys.byteorder)


def read_type(file: BinaryIO, skip_type=False, skip_array_type=False, data_type=0, array_type=0):
    if not skip_type:
        data_type = read_as_int(file, 1)

    if data_type == 1:
        return read_as_int(file, 1)
    elif data_type == 2:
        return read_as_int(file, 2)
    elif data_type == 3:
        return read_as_int(file, 4)
    elif data_type == 4:
        return read_as_int(file, 8)
    elif data_type == 5:
        return struct.unpack('f', file.read(4))
    elif data_type == 6:
        return struct.unpack('d', file.read(8))
    elif data_type == 7:
        if read_as_int(file, 1) == 0:
            return read_as_int(file, 1), read_as_int(file, 1)
        return struct.unpack('2f', file.read(8))
    elif data_type == 8:
        return file.read(read_as_int(file, 2))
    elif data_type == 9:
        return file.read(read_as_int(file, 2)).decode()
    elif data_type == 10:
        return file.read(read_as_int(file, 4))
    elif data_type == 11:
        return file.read(read_as_int(file, 4)).decode()
    elif data_type == 12:
        if not skip_array_type:
            array_type = read_as_int(file, 1)
        array = []

        for i in range(read_as_int(file, 2)):
            array.append(read_type(file, True, False, array_type))


def print_help():
    print('''
Usage:
python sspm_extractor.py [path to .sspm file]
python sspm_extractor.py [option] [path to .sspm file]

Example:
python sspm_extractor.py your_sspm_file.sspm
python sspm_extractor.py -d maps

Options:
-h / --help             Prints this help message
-d / --directory        Extract an entire directory containing .sspm files
-f / --file             Extract a .sspm file (default if not option is provided)
''')


# Handles command line input
def main(args):
    if not args:
        print('You have not provided any file or directory to extract.')
        print_help()
    elif args[0] in ['-h', '--help']:
        print_help()
    elif args[0] in ['-d', '--directory']:
        if len(args) == 1:
            print('Please provide a path to a directory.')
            return
        if not os.path.exists(args[1]):
            print('The path you provided does not exist.')
            print_help()
            return
        elif not os.path.isdir(args[1]):
            print('The path you provided is not a directory.')
            print_help()
            return

        extract_directory(args[1])
    else:
        if args[0] in ['-f', '--file']:
            if len(args) == 1:
                print('Please provide a path to a file.')
                return
            elif not os.path.exists(args[1]):
                print('The path you provided does not exist.')
                return
            elif not os.path.isfile(args[1]):
                print('The path you provided is not a file')
                return
            elif not os.path.splitext(args[1])[1] == '.sspm':
                print('The file you provided does not end in ".sspm".')
                return

            extract_file(args[1])
        else:
            if not os.path.exists(args[0]):
                print('The path you provided does not exist.')
                return
            elif not os.path.isfile(args[0]):
                print('The path you provided is not a file')
                return
            elif not os.path.splitext(args[0])[1] == '.sspm':
                print('The file you provided does not end in ".sspm".')
                return

            extract_file(args[0])


def extract_file(path, extract_dir=False, extract_dir_path=None):
    with open(path, mode='rb') as file:
        # Get amount of markers and difficulty name
        file.seek(0x26)
        marker_count = read_as_int(file, 4)
        difficulty = difficulty_array[read_as_int(file, 1)]

        # Check if file contains audio
        file.read(2)
        has_audio = bool.from_bytes(file.read(1))

        # Check if file contains a cover image
        has_cover = bool.from_bytes(file.read(1))

        # Get audio and cover position in file buffer
        file.seek(0x40)
        audio_offset = read_as_int(file, 8)
        audio_length = read_as_int(file, 8)
        if has_cover:
            cover_offset = read_as_int(file, 8)
            cover_length = read_as_int(file, 8)

        # Marker stuff
        marker_def_offset = read_as_int(file, 8)
        file.seek(0x70)
        marker_offset = read_as_int(file, 8)

        # Get metadata
        file.seek(0x80)
        map_id = read_type(file, True, data_type=9)
        song = read_type(file, True, data_type=9)
        read_type(file, True, data_type=9)  # Value not needed

        # Get mapper(s)
        mappers = ''
        for _ in range(read_as_int(file, 2)):
            mappers += f'{read_type(file, True, data_type=9)}, '
        mappers = mappers.removesuffix(', ')

        # Check for custom difficulty name
        for _ in range(read_as_int(file, 2)):
            key = read_type(file, True, data_type=9)
            value = read_type(file)
            if key == 'difficulty_name' and isinstance(value, str):
                difficulty = value

        # Find audio buffer
        file.seek(audio_offset)
        audio = file.read(audio_length)

        # Check for audio file signatures
        if int.from_bytes(audio[0:4]) == 0x4F676753:
            file_extension = 'ogg'
        elif int.from_bytes(audio[0:4]) == 0x52494646 and int.from_bytes(audio[8:12]) == 0x57415645:
            file_extension = 'wav'
        elif int.from_bytes(audio[0:2]) == 0xFFFB or int.from_bytes(
                audio[0:2]) == 0xFFF3 or int.from_bytes(audio[0:2]) == 0xFFFA or int.from_bytes(
            audio[0:2]) == 0xFFF2 or int.from_bytes(audio[0:3]) == 0x494433:
            file_extension = 'mp3'
        else:
            has_audio = False

        # Get cover image if it exists
        if has_cover:
            file.seek(cover_offset)
            cover = file.read(cover_length)

        # Marker stuff
        markers = {}
        marker_types = []

        file.seek(marker_def_offset)

        for _ in range(read_as_int(file, 1)):
            marker_type = [read_type(file, True, data_type=9)]
            markers[marker_type[0]] = []
            for _ in range(1, read_as_int(file, 1) + 1):
                marker_type.append(read_as_int(file, 1))
            marker_types.append(marker_type)
            file.read(1)

        file.seek(marker_offset)

        for _ in range(marker_count):
            marker = [read_as_int(file, 4)]
            marker_type = marker_types[read_as_int(file, 1)]
            for i in range(1, len(marker_type)):
                marker.append([marker_type[i], read_type(file, True, False, marker_type[i])])

            markers[marker_type[0]].append(marker)

        # Read notes from markers and format it to match SSQE's format
        note_string = f'{map_id},'
        notes = []
        has_notes = True

        if 'ssp_note' in markers.keys():
            for note_data in markers['ssp_note']:
                if note_data[1][0] != 7:
                    continue
                note_time = note_data[0]
                note_x_position = note_data[1][1][0]
                note_y_position = note_data[1][1][1]

                notes.append((2 - note_x_position, 2 - note_y_position, note_time))

            if notes:
                notes = sorted(notes, key=lambda note: note[2])
                for note in notes:
                    note_string += f'{note[0]:.2f}|{note[1]:.2f}|{note[2]},'
            else:
                has_notes = False
            note_string.removesuffix(',')
        else:
            has_notes = False

        # Save data
        if extract_dir:
            save_path = extract_dir_path
        else:
            save_path = os.path.abspath(path.removesuffix('.sspm'))
        audio_file_path = os.path.join(save_path, f'audio.{file_extension}')
        metadata_file_path = os.path.join(save_path, f'metadata.txt')
        cover_file_path = os.path.join(save_path, f'cover.png')
        notes_file_path = os.path.join(save_path, f'notes.txt')
        ssqe_ini_file_path = os.path.join(save_path, f'notes.ini')

        if not os.path.exists(f'{save_path}'):
            os.mkdir(f'{save_path}')
            with open(audio_file_path, 'xb') as audio_file:
                audio_file.write(audio)
                del audio
            with open(metadata_file_path, 'x') as metadata_file:
                metadata_file.write(f'ID: {map_id}\n')
                metadata_file.write(f'Song: {song}\n')
                metadata_file.write(f'Mapper(s): {mappers} \n')
                metadata_file.write(f'Difficulty Name: {difficulty}\n')
            if has_cover:
                with open(cover_file_path, 'xb') as cover_file:
                    cover_file.write(cover)
            with open(notes_file_path, 'x') as note_file:
                note_file.write(note_string)
            with open(ssqe_ini_file_path, 'x') as ssqe_ini_file:
                ssqe_ini_file.write(
                    f'{{"beatDivisor": 2, "bookmarks": [], "cover": "{"cover.png" if has_cover else "Default"}", "currentTime": 0, "customDifficulty": "{"" if difficulty in difficulty_array else difficulty}", "difficulty": "{difficulty}", "exportOffset": 0, "mappers": "{mappers}", "songName": "{song}", "timings": [], "useCover": {"true" if has_cover else "false"}}}')

            if not extract_dir:
                print(f'''Audio: {"Extracted successfully" if has_audio else "Could not be extracted"}
    Cover: {"Extracted successfully" if has_cover else "Could not be extracted or does not exist"}
    Notes: {"Extracted successfully" if has_notes else "Could not be extracted"}
    
    Your files are in {save_path} :)
    ''')
        else:
            if not extract_dir:
                print('A folder with this map\'s ID already exists. Are you sure you haven\'t extracted it before?')
            return


def progress_bar(value, max_value, length):
    progress = int(value / max_value * length)
    left = length - progress

    print(f'Progress:\n[{"=" * progress}{" " * left}] ({value}/{max_value})')


def extract_directory(path):
    files = glob('*.sspm', root_dir=path)
    print(files)
    if not files:
        print('There are no .sspm files in the directory you provided.')
        return

    extracted_path = os.path.abspath(path + '_extracted')

    if not os.path.exists(extracted_path):
        os.mkdir(extracted_path)
    else:
        print(
            f'The folder\ {path + "_extracted"} already exists. Are you sure you haven\'t extracted this directory before?')
        return

    successfully_extracted = 0
    for i, file in enumerate(files):
        try:
            extract_file(os.path.join(path, file), True, os.path.join(extracted_path, os.path.splitext(file)[0]))
            successfully_extracted += 1
        except:  # Sorry
            pass
        finally:
            clear()
            progress_bar(i + 1, len(files), 40)

    print(f'\nSuccessfully extracted {successfully_extracted}/{len(files)} .sspm files.')
    print(f'Your files are in {extracted_path} :)')


if __name__ == '__main__':
    main(sys.argv[1:])
