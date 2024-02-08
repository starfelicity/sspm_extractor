import struct
import sys
import os
from typing import BinaryIO

difficulty_array = [
    'N/A',
    'Easy',
    'Normal',
    'Hard',
    'LOGIC?!',
    'Tasukete'
]


def read_as_int(file, byte_amount: int):
    return int.from_bytes(file.read(byte_amount), byteorder=sys.byteorder)


def read_type(file: BinaryIO, skip_type=False, skip_array_type=False, data_type=0, array_type=0):
    if not skip_type:
        data_type = read_as_int(file, 1)


    # I'd use a match statement but then this wouldn't work on anything before python 3.10
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
    print(
'''
Usage:
python sspm_extractor.py [path to .sspm file]
'''
    )


def main(args):
    if not args:
        return
    elif args[0] in ['-h', '--help']:
        print_help()
    elif not os.path.isfile(args[0]) or os.path.splitext(args[0])[1] != '.sspm':
        print("Input file does not exist or is invalid.\n")
        print_help()
        return

    with open(args[0], mode='rb') as file:
        # Get amount of markers and difficulty name
        file.seek(0x26)
        marker_count = read_as_int(file, 4)
        difficulty = difficulty_array[read_as_int(file, 1)]

        # Check if file contains audio
        file.read(2)
        if not bool.from_bytes(file.read(1)):
            print('The file doesn\'t contain music / is broken.')
            return

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
            print('The audio buffer contained in the file can\'t be read.')
            return

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
                print('This map contains no notes / No notes could be found.')
            note_string.removesuffix(',')
        else:
            print('This map contains no notes / No notes could be found.')

        # Save data
        save_path = f'{args[0].removesuffix(".sspm")}'
        audio_file_path = os.path.join(save_path, f'audio.{file_extension}')
        metadata_file_path = os.path.join(save_path, f'metadata.txt')
        cover_file_path = os.path.join(save_path, f'cover.png')
        notes_file_path = os.path.join(save_path, f'notes.txt')
        ssqe_ini_file_path = os.path.join(save_path, f'song.ini')

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
                ssqe_ini_file.write(f'{{"beatDivisor": 2, "bookmarks": [], "cover": "{"cover.png" if has_cover else "Default"}", "currentTime": 0, "customDifficulty": "{"" if difficulty in difficulty_array else difficulty}", "difficulty": "{difficulty}", "exportOffset": 0, "mappers": "{mappers}", "songName": "{song}", "timings": [], "useCover": {"true" if has_cover else "false"}}}')
        else:
            print('A folder with this map\'s ID already exists. Are you sure you haven\'t extracted it before?')
            return


if __name__ == '__main__':
    main(sys.argv[1:])