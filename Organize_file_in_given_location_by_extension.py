# -*- coding: utf-8 -*-
"""
Created on Thu Apr 11 21:55:29 2024

@author: BISHU
"""

import os
import shutil

def organize_files(folder_path):
    # Get all files in the folder
    files = os.listdir(folder_path)
    
    # Create a set to store unique file extensions
    extensions = set()
    
    # Get unique file extensions
    for file_name in files:
        _, file_extension = os.path.splitext(file_name)
        if file_extension:
            extensions.add(file_extension)
    
    # Create folders for each unique file extension
    for extension in extensions:
        folder_name = extension[1:]  # Remove the dot from the extension
        os.makedirs(os.path.join(folder_path, folder_name), exist_ok=True)
    
    # Move files to corresponding folders based on their extensions
    for file_name in files:
        _, file_extension = os.path.splitext(file_name)
        if file_extension:
            folder_name = file_extension[1:]
            src_path = os.path.join(folder_path, file_name)
            dst_path = os.path.join(folder_path, folder_name, file_name)
            try:
                shutil.move(src_path, dst_path)
            except Exception as e:
                print(f"Error moving file {file_name}: {e}")


            
#%%
            
# Example usage
folder_location = r"C:\Users\BISHU\Videos\test"
organize_files(folder_location)
