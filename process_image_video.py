import os
import subprocess
import sys
import time # Import the time module
from PIL import Image
from moviepy.editor import VideoFileClip, AudioFileClip, AudioClip, vfx, concatenate_audioclips

def clear_folder(folder_path):
    """
    Clears all files from the specified folder, but does not delete the folder itself.
    If the folder does not exist, it will be created.
    """
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Created folder: {folder_path}")
        return

    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                # If there are subdirectories, remove them recursively
                import shutil
                shutil.rmtree(file_path)
            print(f"Cleared {file_path}")
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")
    print(f"Folder '{folder_path}' cleared.")

def filter_and_delete_images(image_folder="images"):
    """
    Deletes images from the specified folder based on the following criteria:
    - Image has the same height and width (square image)
    - Image has a height less than 600px
    - Image has a width less than 600px
    - Image has a width greater than its height (landscape orientation)
    """
    if not os.path.exists(image_folder):
        print(f"Error: Image folder '{image_folder}' not found.")
        return

    deleted_count = 0
    for filename in os.listdir(image_folder):
        filepath = os.path.join(image_folder, filename)
        if not os.path.isfile(filepath):
            continue

        try:
            with Image.open(filepath) as img:
                width, height = img.size

                delete_image = False
                reasons = []

                # Condition 1: Same height and width
                if width == height:
                    delete_image = True
                    reasons.append("same height and width")

                # Condition 2: Height less than 600px
                if height < 600:
                    delete_image = True
                    reasons.append("height less than 600px")

                # Condition 3: Width less than 600px
                if width < 600:
                    delete_image = True
                    reasons.append("width less than 600px")

                # Condition 4: Width > height (landscape)
                if width > height:
                    delete_image = True
                    reasons.append("width > height")

                if delete_image:
                    img.close()  # Explicitly close the image file
                    os.remove(filepath)
                    deleted_count += 1
                    print(f"Deleted '{filename}' (W:{width}, H:{height}) because: {', '.join(reasons)}")

        except Exception as e:
            print(f"Could not process image '{filename}': {e}")

    print(f"\nFinished filtering. Total images deleted: {deleted_count}")

def resize_images(input_folder="images", output_folder="resized_images", size=(720, 1280)):
    """
    Resizes all images in the input_folder to the specified size (width, height)
    and saves them to the output_folder. Images are squeezed or stretched, not cropped.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    for filename in os.listdir(input_folder):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
            input_path = os.path.join(input_folder, filename)
            output_path = os.path.join(output_folder, filename)

            try:
                with Image.open(input_path) as img:
                    # Resize the image without maintaining aspect ratio (squeeze/stretch)
                    resized_img = img.resize(size, Image.LANCZOS)
                    resized_img.save(output_path)
                print(f"Resized {filename} to {size[0]}x{size[1]} and saved to {output_folder}")
            except Exception as e:
                print(f"Error processing {filename}: {e}")

def create_video_from_image(image_path, output_dir="videos", duration=5, background_music_path=None, music_start_time=0):
    """
    Converts a single image into a video of specified duration using ffmpeg and adds background music.

    Args:
        image_path (str): The path to the input image file.
        output_dir (str): The directory where the output video will be saved.
        duration (int): The duration of the video in seconds.
        background_music_path (str, optional): Path to the background music file.
        music_start_time (int, optional): Time in seconds from which the music should start in the video.
    """
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return

    os.makedirs(output_dir, exist_ok=True)

    image_filename = os.path.basename(image_path)
    video_filename_base = os.path.splitext(image_filename)[0]
    output_video_path_no_audio = os.path.join(output_dir, f"{video_filename_base}_no_audio.mp4")
    final_output_video_path = os.path.join(output_dir, f"{video_filename_base}.mp4")

    # ffmpeg command to create video from image
    command = [
        "ffmpeg",
        "-loop", "1",
        "-i", image_path,
        "-t", str(duration),
        "-vf", "fps=25",
        "-pix_fmt", "yuv420p",
        "-y",
        output_video_path_no_audio
    ]

    try:
        print(f"Creating video from {image_path}...")
        subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print(f"Video created successfully: {output_video_path_no_audio}")
    except subprocess.CalledProcessError as e:
        print(f"Error creating video: {e}")
        print(f"ffmpeg stdout: {e.stdout.decode()}")
        print(f"ffmpeg stderr: {e.stderr.decode()}")
        return
    except FileNotFoundError:
        print("Error: ffmpeg not found. Please ensure ffmpeg is installed and in your system's PATH.")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return

    if background_music_path and os.path.exists(background_music_path):
        try:
            video_clip = VideoFileClip(output_video_path_no_audio)
            audio_clip = AudioFileClip(background_music_path)

            # Ensure the audio clip does not exceed the remaining video duration.
            # We take a subclip of the audio, limited by the video's remaining duration.
            # Create a silent audio clip for the initial duration
            silent_clip = AudioClip(make_frame=lambda t: 0, duration=music_start_time)

            # Trim the actual music clip to fit the remaining video duration
            trimmed_music_clip = audio_clip.subclip(0, min(audio_clip.duration, video_clip.duration - music_start_time))

            # Concatenate the silent clip and the trimmed music clip
            final_audio = concatenate_audioclips([silent_clip, trimmed_music_clip])

            final_video = video_clip.set_audio(final_audio)

            print(f"Adding background music from {music_start_time}s to video...")
            final_video.write_videofile(final_output_video_path, codec="libx264", audio_codec="aac")
            print(f"Video with music created successfully: {final_output_video_path}")

            # Clean up the intermediate video without audio
            os.remove(output_video_path_no_audio)

        except Exception as e:
            print(f"Error adding background music: {e}")
    else:
        print(f"No background music added. Music file not found or path not provided: {background_music_path}")
        # If no music, just rename the no-audio video to the final name
        os.rename(output_video_path_no_audio, final_output_video_path)


def main():
    # Clear output folders at the beginning
    print("Clearing resized_images and videos folders...")
    clear_folder("resized_images")
    clear_folder("videos")
    print("Folders cleared. Waiting for 5 seconds for visual confirmation...")
    time.sleep(5) # Wait for 5 seconds
    print("Resuming program execution.")

    # Step 1: Filter and delete images
    print("Starting image filtering...")
    filter_and_delete_images(image_folder="images")
    print("Image filtering completed.")

    # Step 2: Resize images
    print("\nStarting image resizing...")
    resize_images(input_folder="images", output_folder="resized_images", size=(720, 1280))
    print("Image resizing completed.")

    # Step 3: Create video from resized images
    print("\nStarting video creation...")
    resized_images_dir = "resized_images"
    background_music_file = "background_music/bell.mp3"
    
    if not os.path.exists(resized_images_dir):
        print(f"Error: Directory '{resized_images_dir}' not found for video creation.")
        sys.exit(1)

    image_files = [f for f in os.listdir(resized_images_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))]
    image_files.sort() # Ensure consistent order

    if not image_files:
        print(f"No image files found in '{resized_images_dir}' for video creation.")
        sys.exit(0)

    for image_file in image_files:
        image_path = os.path.join(resized_images_dir, image_file)
        create_video_from_image(image_path, duration=5, background_music_path=background_music_file, music_start_time=1)
    print("Video creation completed for all images.")

if __name__ == "__main__":
    main()
