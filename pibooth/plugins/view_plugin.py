# -*- coding: utf-8 -*-

import pibooth
from pibooth.utils import LOGGER, get_crash_message, PoolingTimer
import tkinter as tk
from tkinter import *
from pibooth.counters import Counters
from pibooth.nameholder import Nameholder
from configparser import RawConfigParser
from pibooth.config.parser import PiConfigParser
import customtkinter as ctk
from PIL import Image

class ViewPlugin(object):

    """Plugin to manage the pibooth window dans transitions.
    """

    name = 'pibooth-core:view'

    def __init__(self, plugin_manager):
        #self._config = PiConfigParser(RawConfigParser)
        self._pm = plugin_manager
        self.personName = ''
        self.count = 0
        self.forgotten = False
        self.newRun = False
        self.newRunStart = False
        # Seconds to display the failed message
        self.failed_view_timer = PoolingTimer(2)
        # Seconds between each animated frame
        self.animated_frame_timer = PoolingTimer(0)
        # Seconds before going back to the start
        self.choose_timer = PoolingTimer(30)
        # Seconds to display the selected layout
        self.layout_timer = PoolingTimer(4)
        # Seconds to display the selected layout
        self.print_view_timer = PoolingTimer(0)
        # Seconds to display the selected layout
        self.finish_timer = PoolingTimer(1)
        
        #self.nameholder = Nameholder(self._config.join_path("nameholder.pickle"),
         #             name="",
          #            remaining_duplicates=self._config.getint('PRINTER', 'max_duplicates'))



    @pibooth.hookimpl
    def state_failsafe_enter(self, win):
        win.show_oops()
        self.failed_view_timer.start()
        LOGGER.error(get_crash_message())

    @pibooth.hookimpl
    def state_failsafe_validate(self):
        if self.failed_view_timer.is_timeout():
            return 'wait'

    @pibooth.hookimpl
    def state_wait_enter(self, cfg, app, win):
        if app.nameofperson:
            self.newRun = True
        self.forgotten = False
        if app.previous_animated:
            previous_picture = next(app.previous_animated)
            # Reset timeout in case of settings changed
            self.animated_frame_timer.timeout = cfg.getfloat('WINDOW', 'animate_delay')
            self.animated_frame_timer.start()
        else:
            previous_picture = app.previous_picture
            
        '''win.show_intro(previous_picture, app.printer.is_ready()
                       and app.count.remaining_duplicates > 0)'''
        if app.printer.is_installed():
            win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())

    @pibooth.hookimpl
    def state_wait_do(self, app, win, events):
        #LOGGER.info('futogatok')
        if app.previous_animated and self.animated_frame_timer.is_timeout():
            previous_picture = next(app.previous_animated)
            '''win.show_intro(previous_picture, app.printer.is_ready()
                           and app.count.remaining_duplicates > 0)'''
            self.animated_frame_timer.start()
        else:
            previous_picture = app.previous_picture

        event = app.find_print_status_event(events)
        if event and app.printer.is_installed():
            tasks = app.printer.get_all_tasks()
            win.set_print_number(len(tasks), not app.printer.is_ready())

        if app.find_print_event(events) or (win.get_image() and not previous_picture):
            '''win.show_intro(previous_picture, app.printer.is_ready()
                           and app.count.remaining_duplicates > 0)'''
            
        Popup = Popupwindowka(app)
        Popup.mainloop()
        
        if Popup.nameofperson is None:
            app.nameofperson = None
            
        if Popup.nameofperson is not None:
            if Popup.nameofperson != "":
                #LOGGER.info("asd : " + Popup.nameofperson)
                app.nameofperson = Popup.nameofperson
                self.newRunStart = True
        
        '''if self.newRun:
            result = self.ask_question(app)
            LOGGER.info(result)
            if result:
                self.newRun = False
                self.newRunStart = True

            else:
                self.newRun = False
                app.nameofperson = None
                '''
        
            
    @pibooth.hookimpl
    def state_wait_validate(self, cfg, app, events):
        if app.find_capture_event(events) or self.newRunStart:
            self.newRunStart = False
            if len(app.capture_choices) > 1:
                if not app.nameofperson:
                    self.show_popup(app)
                return 'choose'
            if cfg.getfloat('WINDOW', 'chosen_delay') > 0:
                if not app.nameofperson:
                    self.show_popup(app)
                return 'chosen'
            return 'preview'

    @pibooth.hookimpl
    def state_wait_exit(self, win):
        self.count = 0
        win.show_image(None)  # Clear currently displayed image

    @pibooth.hookimpl
    def state_choose_enter(self, app, win):
        LOGGER.info("1 Show picture choice (nothing selected)")
        win.set_print_number(0, False)  # Hide printer status
        win.show_choice(app.capture_choices)
        self.choose_timer.start()

    @pibooth.hookimpl
    def state_choose_validate(self, cfg, app):
        if app.capture_nbr:
            if cfg.getfloat('WINDOW', 'chosen_delay') > 0:
                return 'chosen'
            else:
                return 'preview'
        elif self.choose_timer.is_timeout():
            return 'wait'

    @pibooth.hookimpl
    def state_chosen_enter(self, cfg, app, win):
        LOGGER.info("1 Show picture choice (%s captures selected)", app.capture_nbr)
        win.show_choice(app.capture_choices, selected=app.capture_nbr)

        # Reset timeout in case of settings changed
        self.layout_timer.timeout = cfg.getfloat('WINDOW', 'chosen_delay')
        self.layout_timer.start()

    @pibooth.hookimpl
    def state_chosen_validate(self):
        if self.layout_timer.is_timeout():
            return 'preview'

    @pibooth.hookimpl
    def state_preview_enter(self, app, win):
        self.count += 1
        win.set_capture_number(self.count, app.capture_nbr)

    @pibooth.hookimpl
    def state_preview_validate(self):
        return 'capture'

    @pibooth.hookimpl
    def state_capture_do(self, app, win):
        win.set_capture_number(self.count, app.capture_nbr)

    @pibooth.hookimpl
    def state_capture_validate(self, app):
        if self.count >= app.capture_nbr:
            return 'processing'
        return 'preview'

    @pibooth.hookimpl
    def state_processing_enter(self, win):
        win.show_work_in_progress()

    @pibooth.hookimpl
    def state_processing_validate(self, cfg, app):
        if app.printer.is_ready() and cfg.getfloat('PRINTER', 'printer_delay') > 0\
                and app.count.remaining_duplicates > 0:
            return 'print'
        return 'finish'  # Can not print

    @pibooth.hookimpl
    def state_print_enter(self, cfg, app, win):
        LOGGER.info("Display the final picture")
        win.show_print(app.previous_picture)
        win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())

        # Reset timeout in case of settings changed
        self.print_view_timer.timeout = cfg.getfloat('PRINTER', 'printer_delay')
        self.print_view_timer.start()

    @pibooth.hookimpl
    def state_print_validate(self, app, win, events):
        printed = app.find_print_event(events)
        self.forgotten = app.find_capture_event(events)
        if self.print_view_timer.is_timeout() or printed or self.forgotten:
            if printed:
                win.set_print_number(len(app.printer.get_all_tasks()), not app.printer.is_ready())
            return 'finish'

    @pibooth.hookimpl
    def state_finish_enter(self, cfg, app, win):
        if cfg.getfloat('WINDOW', 'finish_picture_delay') > 0 and not self.forgotten:
            win.show_finished(app.previous_picture)
            timeout = cfg.getfloat('WINDOW', 'finish_picture_delay')
        else:
            win.show_finished()
            timeout = 1

        # Reset timeout in case of settings changed
        self.finish_timer.timeout = timeout
        self.finish_timer.start()

    @pibooth.hookimpl
    def state_finish_validate(self):
        if self.finish_timer.is_timeout():
            return 'wait'

#-----------------------------------------------
# UTILITY HELPER FUNCTIONS

    def show_popup(self,app):        
        '''root = tk.Tk()
        root.withdraw()
        
        result = simpledialog.askstring("Input","Enter something:")
        
        while result is None:
            root.update()
            result = simpledialog.askstring("Input","Enter something:")

            #for name in nameholder:
            #    setattr(nameholder, name, personName)
            
        app.nameofperson = result
        LOGGER.info("name:" + app.nameofperson)
        LOGGER.info(result)
        '''
        
        root = ctk.CTk()
        root.geometry("0x0+1000+1000")
                
        result = None
        LOGGER.info("step1")
        dialog = ctk.CTkInputDialog(text="Enter your company email / Írd be az NI-os email címed",title="Email")
        LOGGER.info("step2")
        dialog.geometry("+1000+500")
        
        while result is None:
            root.update()
            LOGGER.info("bejottem hihi")
            result = dialog.get_input()
            if result == "":
                result = None
            
            if result is None:
                root.destroy()
                root = ctk.CTk()
                root.geometry("0x0+1000+1000")
                dialog = ctk.CTkInputDialog(text="Enter your company email / Írd be az NI-os email címed",title="Email")
                dialog.geometry("+1000+500")

            LOGGER.info(result)

        root.destroy()
        return result
        
        
     
    def ask_question(self,app):
        root = tk.Tk()
        root.withdraw()
        
        height=540
        width=960
        
        root.geometry(f'{height}x{width}+1000+0')
        result = None
        
        while result is None:
            root.update()
            result = messagebox.askyesno("További kép","""
Szeretnél ezzel az email címmel további képeket készíteni?
Email:{}""".format(app.nameofperson))

        if result:
            self.newRun = False
        else:
            self.newRun = False
            app.nameofperson = None
            
        root.destroy()
        return result
    
    
    def popupwindow(self,app):
        root = ctk.CTk()
        root.geometry("1080x1920")
        root.title("Photo Booth")
        

class Popupwindowka(ctk.CTk):
    def __init__(self,app):
        ctk.set_appearance_mode("dark")
        super().__init__()
        self.geometry("1080x1920")
        self.title("Photo Booth")
        self.emailReady = False
        self.emailTypedIn = ""
        
        self.nameofperson = app.nameofperson
        self.previous_picture = app.previous_picture
        # Ha van email beirva, kerdes, hogy kell e uj kep
        if self.nameofperson is not None:
            self.popup_additional_photo()
            
        # Ha nem vagy nincs beirva nev akkor intro
        if self.nameofperson is None:
            my_image = ctk.CTkImage(light_image=Image.open("/home/pi/pibooth/pibooth/plugins/Intro.png"),
                                    dark_image=Image.open("/home/pi/pibooth/pibooth/plugins/Intro.png"),
                                    size=(1080,1920))
            self.image_label = ctk.CTkLabel(self,image=my_image,text="")
            self.image_label.place(x = 0,y = 0)
            self.button = ctk.CTkButton(self,
                                        fg_color="#006b46",
                                        font=("Verdana",16),
                                        border_color="#000",
                                        hover_color="#009b65",
                                        text="Start",
                                        command=self.popup_button_close)
            self.button.pack(padx=20,pady=897)
            
        # Utana email beiras
        
        
    def popup_button_close(self):
        self.image_label.destroy()
        self.button.destroy()
        self.popup_email_entry()
        #self.destroy()
        
    def popup_email_window_creator(self):
            
                      
        self.MainFrame = Frame(self, width=1080, height=490, relief = RIDGE, background='#2e2e2e')
        self.MainFrame.place(x=0,y=800)

    
        pushKeysBy = 2    
        keys = [
                ['1','2','3','4','5','6','7','8','9','0','-','=','Back\nVissza'],
                ['Q','W','E','R','T','Y','U','I','O','P','[',']','Delete\nTörlés'],
                ['A','S','D','F','G','H','J','K','L',';','~',',','@ni.com'],
                ['Z','X','C','V','B','N','M','.','@','@ni.com','#','?']

            ]
        
        
        '''for i, key_row in enumerate(keys):
            for j, key in enumerate(key_row):
                tk.Button(MainFrame, background='black', font=("Verdana",14,"bold"), foreground='white',text=key, width=6, height=6).grid(row=i+pushKeysBy, column=j)
           '''
        
        def button_click(key):
            currentLen = len(str(entry.get()))
            if key=="Back\nVissza":
                entry.delete(currentLen-1,currentLen)
            elif key=="Delete\nTörlés":
                entry.delete(0,currentLen)
            else:
                entry.insert(currentLen,str(key).lower())
                
        def submit_email(self):
            self.emailTypedIn = str(entry.get())
            
            
        
        instruction = ctk.CTkLabel(self.MainFrame,width=1080,font=("Verdana",28),text="Kérlek, írd be a céges e-mail címed.\n\nPlease, enter your company email address.",pady=10)
        instruction.grid(row=0,column=0,columnspan=len(keys[0]),pady=10)
        
        entry = tk.Entry(self.MainFrame,font=('arial',28,'bold'),bd=5,width=48)
        entry.grid(row=1, column=0, columnspan=len(keys[0]), pady=10)
        
        for i, key_row in enumerate(keys):
            for j, key in enumerate(key_row):
                tk.Button(self.MainFrame, background='#3e3e3e', foreground='white',command = lambda key = key: button_click(key), text=key, width=6, height=6).grid(row=i+pushKeysBy, column=j)
                

        tk.Button(self.MainFrame, background='#3e3e3e', foreground='white',command = lambda self = self: submit_email(self), text="OK", width=48, height=6,pady=20).grid(row=len(keys[0]), column=0,columnspan=len(keys[0]))
        
    def popup_email_entry(self):
        
        result = None
        self.emailReady = False
        
        self.popup_email_window_creator()
        while result == "" or result is None:
            self.update()
            result = self.emailTypedIn
            #result = self.dialog.get_input()
                
            '''if result == "":
                self.MainFrame.destroy()
                #self.dialog.destroy()
                self.popup_email_window_creator()'''
        
        LOGGER.info(result)
        print("asdasd ------ " + result)
        self.nameofperson = result
        self.destroy()
    
    def popup_additional_photo(self):
        self.questionlabeleng = ctk.CTkLabel(self,width=1080,font=("Verdana",35),text="Would you like to take one more picture?")
        self.questionlabelhun = ctk.CTkLabel(self,width=1080,font=("Verdana",35),text="Szeretnél még egy képet készíteni?")
        self.questionlabeleng.place(x = 0, y = 200)
        self.questionlabelhun.place(x = 0, y = 250)
        
        self.email = ctk.CTkLabel(self,width=1080,font=("Verdana",35),text="{}".format(self.nameofperson),text_color="#009b65")
        self.email.place(x = 0,y = 500)
        
        previmage = ctk.CTkImage(light_image=self.previous_picture,dark_image=self.previous_picture,size=(400,600))
        self.prevlabel = ctk.CTkLabel(self,width=1080,image=previmage,text="")
        self.prevlabel.place(x=0,y=600)
        self.agreebutton = ctk.CTkButton(self,
                            fg_color="#006b46",
                            font=("Verdana",24),
                            border_color="#000",
                            hover_color="#009b65",
                            text="Yes / Igen",
                            width=500,height=180,
                            command=self.additional_photo_button_agree)
        
        self.disagreebutton = ctk.CTkButton(self,
                    fg_color="#dc3545",
                    font=("Verdana",24),
                    border_color="#000",
                    hover_color="#d63384",
                    text="No / Nem",
                    width=500,
                    height=180,
                    command=self.additional_photo_button_disagree)

        self.agreebutton.place(x=290,y=1400)
        self.disagreebutton.place(x=290,y=1600)
        self.update()
        
        
    def additional_photo_button_agree(self):
        self.destroy()
        
    def additional_photo_button_disagree(self):
        self.nameofperson = None
        self.destroy()