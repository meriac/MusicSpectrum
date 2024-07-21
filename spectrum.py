#!/usr/bin/python3

#
#  Music Notes Detection Algorithm using Wavelets
#

#  Copyright 2025 Milosch Meriac <milosch@meriac.com>
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

from PIL import Image
import numpy as np
import scipy.signal as sig
import scipy.io.wavfile as sigwav
import matplotlib.pyplot as plt

ColsPerSecond = 25*12

def wavelet(Fs, Fw, N=11):

    samples = int(N*Fs/Fw)|1
    t = np.arange(0, samples)/Fs

    # Calculate wavelet sine
    wave = np.exp(2j * np.pi * Fw * t)

    # Calculate wavelet envelope
    duration = samples / Fs
    envelope = (1-np.cos((2*np.pi/duration)*t))/2

    return -wave * envelope

def wavelet_harmonics(Fs, Fw, Fmax=0, N=11, harmonics_step=2):

    # Set wavelet maximum order frequency to Fs/5 and lower by default
    if Fmax<=0:
        Fmax = Fs/5

    # Calculate base frequency and harmonics
    res = False
    scale = 0
    order = 1

    while True:
        # Maintain count of scale and order
        scale += 1/order

        freq = Fw*order
        if freq>Fmax:
            break

        # Add all harmonics wavelets together, attenuated by harmonics order
        w = wavelet(Fs, freq, N)/order
        if order==1:
            mid = len(w)//2
            res = w
        else:
            i = len(w)//2
            res[mid-i:mid+i+1] += w

        order += harmonics_step

    # Return mirrored and normalized wavelet
    return res/scale

def wavelet_notes(octaves=8):
    return 27.5 * 2 ** (np.arange(octaves*12) / 12)

def wavelet_palette(colormap, num_colors):
    # Use matplotlib to generate a rainbow colormap ...
    cmap = plt.get_cmap(colormap)

    # ... and return RGB uint8[3] color palette
    indices = np.linspace(0, 1, num_colors)
    return (cmap(indices)[:, :3] * 255).astype(np.uint8)

def wavelet_image(image, colormap='terrain', num_colors=4096):

    # Retrieve color palette
    rgb_palette = wavelet_palette(colormap, num_colors)

    # Convert image to 16 bit integer ...
    image = (((num_colors-1)/np.max(image))*image).astype(np.uint16)
    # ... and convert to image
    return Image.fromarray(rgb_palette[image])


# Read WAV file for analysis ...
Fs, signal = sigwav.read('spectrum.wav')
if signal.ndim>1:
    signal = np.mean(signal, axis=1)
# ... and transform to normalized complex
signal = sig.hilbert(signal)
signal /= np.max(np.abs(signal))

# Calculate all convolutions - one per musical note
notes = wavelet_notes()
notes_count = len(notes)
image = np.empty((len(notes),len(signal)), dtype=float)
for i, Fw in enumerate(notes):
    print(f'\rScanning note {Fw:.1f}Hz [{(i+1)/notes_count:.0%}]... ', end='')
    w = wavelet_harmonics(Fs, Fw)
    # sigwav.write(f'wavelet-{Fw:.1f}.wav', Fs, np.stack((w.real, w.imag), axis=-1))
    image[notes_count-i-1] = np.abs(sig.convolve(signal, w,'same'))

# Determine downsampling-factor
Downsampling = Fs // ColsPerSecond
image = np.clip(sig.decimate(image, Downsampling), 0, np.max(image))

# Convert image array to image object
img_out = wavelet_image(image)
img_out.save('spectrum.tiff')

# Dump processing status at the end
print(f'\n[DONE] Fs:{Fs} cps:{ColsPerSecond} Downsampling:Fs/cps={Downsampling}')

# HowTo convert spectrum.tiff into a scrolling movie:
# ffmpeg -y -loop 1 -i spectrum.tiff -i spectrum.wav -vf "pad=iw+4096:ih:0:0,scale=iw:ih*5,crop=ih*16/9:ih:y=0:x=12*n" -r 25 -c:v libx264 -crf 25 -pix_fmt yuv420p -c:a aac -b:a 192k -shortest spectrum.mp4