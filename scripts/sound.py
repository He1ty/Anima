import pygame


class Sound:
    def __init__(self,game,sounds_paths:dict,is_music:bool,master_volume,volume:float = 1):
        self.game = game
        self.volume = volume
        self.is_music = is_music
        self.sounds_paths = sounds_paths
        self.sounds = {}
        self.master_volume = master_volume

        for sound_key, path in self.sounds_paths.items():
            if path:
                try:
                    if not self.is_music:
                        self.sounds[sound_key] = pygame.mixer.Sound(path)
                    else:
                        self.music_paths = self.sounds_paths
                except Exception as e:
                    print(f"Erreur lors du chargement du son '{sound_key}': {e}")

    def play(self, name, loops=0):
        """
        Play a sound.
        :param name: The key of the sound in the dictionary
        :param loops: The number of times to loop the sound. -1 for infinity
        :return:
        """
        if self.is_music:
            try:
                pygame.mixer.music.load(self.music_paths[name])
                pygame.mixer.music.set_volume(self.volume*self.master_volume)
                pygame.mixer.music.play(loops)
            except :
                pass
        else:
            self.sounds[name].play()

    def stop(self,name=None):
        if self.is_music:
            pygame.mixer.music.stop()
        else:
            if name:
                self.sounds[name].stop()

    def set_volume(self, volume):
        self.volume = volume
        if self.is_music:
            pygame.mixer.music.set_volume(self.master_volume * volume)
        else:
            for sound in self.sounds.values():
                sound.set_volume(self.master_volume * volume)
