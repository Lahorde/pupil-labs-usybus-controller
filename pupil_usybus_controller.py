from plugin import Plugin
from pyglui.cygl.utils import draw_points_norm,RGBA
from pyglui import ui
from ivy.std_api import *
import socket
import pkg_resources
import configparser
import datetime
import ivy

'''
Interface with pupillabs eye tracker. 
Pupilabs events -> published on Usybus
For info about pupillabs plugins 
https://github.com/pupil-labs/pupil/wiki/Plugin-Guide    
'''
class PupilUsybusController(Plugin):
    device_id = 'pupil_usybus_controller'   	
    
    
    def __init__(self, g_pool):
        super(PupilUsybusController, self).__init__(g_pool)
        self.order = .8
        self.pupil_display_list = []
        # keep last 100 timestamps
        self.last_gaze_tcs = [] 
        self.last_pupils_tcs = [] 
        
        self.send_tc = False 
        self.send_gaze = False 
        self.pupil_epoch = None
        self.confidence = 0.6
        
        self.app_name = '{}@{}'.format(self.__class__.__name__ , socket.gethostname()) 

        # initialising the bus
        IvyInit(agent_name=self.app_name,                                                                  # application name for Ivy
                ready_msg='UB2;type=usybus;from={};ivy_version={}'.format(self.app_name, ivy.__version__), # ready_msg
                main_loop_type_ignored=0,                                                                  # main loop is local (ie. using IvyMainloop)
                on_cnx_fct=PupilUsybusController.on_ivy_conn,                                              # handler called on connection/disconnection
                on_die_fct=PupilUsybusController.on_ivy_die)                                               # handler called when a <die> message is received
        
        # read plugin configuration file
        config = configparser.ConfigParser()
        config_file = config.read('pupil_usybus_controller.cfg')
        address = ''

        if len(config_file) == 0 :
            print('no config file')
        else :
            try :
                address = config.get('config', 'address')
            except configparser.NoOptionError :
                pass
        
        # starting the bus
        # Note: env variable IVYBUS will be used if no parameter or empty string
        # is given ; this is performed by IvyStart (C)
        IvyStart(address)
       
       
    def init_gui(self):
        # initialize the menu
        self.menu = ui.Scrolling_Menu('Usybus controller')
        # add menu to the window
        self.g_pool.gui.append(self.menu)
        self.menu.append(ui.Button('Close', self.unset_alive))
        self.menu.append(ui.Button('Reset', self.reset))
        self.menu.append(ui.Switch('send_tc',self,label='Send TC')) 
        self.menu.append(ui.Switch('send_gaze',self,label='Send Gaze')) 
        self.menu.append(ui.Text_Input('device_id',self,setter=PupilUsybusController.set_device_id))
        self.menu.append(ui.Slider('confidence',self,min=0.1,step=0.01,max=1.0,label='Confidence')) 


    def start_tracking(self):
        pass
    
    
    def reset(self):
        # TODO check if synchro mechanisms needed
        self.last_gaze_tcs = [] 
        self.last_pupils_tcs = [] 
        
    
    def reset_tracking(self):
        pass


    def deinit_gui(self):
        if self.menu:
            self.g_pool.gui.remove(self.menu)
            self.menu = None


    def unset_alive(self):
        self.alive = False

    def capture_update(self,frame,events):  
       self.publish_gaze(frame,events, self.g_pool.eyes_are_alive[0].value, self.g_pool.eyes_are_alive[0].value)   
       
    def player_update(self,frame,events):
       self.publish_gaze(frame,events, True, True)   
       
    def publish_gaze(self,frame,events, left_eye, right_eye):
        # Refer here for data format https://github.com/pupil-labs/pupil/wiki/Data-Format
        # TODO check data for both eyes
        
        '''
        Handle gaze positions. A given gaze_position refer to right/left eye gaze. To get corresponding eye, base_data must be check.
        => in order to publish a gaze (both eyes) on UB, several eye gazes must be captured and a left - right eyes gaze must be built
        from these gaze having different timestamps
        '''
        for pt in events.get('gaze_positions',[]):
            # Is left pupil ? Is Right pupil? 
            gaze_pupils = [False, False]

            # check if data has already been handled 
            if not pt['timestamp'] in self.last_gaze_tcs :
                if self.pupil_epoch is None :
                    system_tc = (datetime.datetime.now() - datetime.datetime(1970, 1, 1, 0, 0)).total_seconds()*1000
                    # pupil timestamps are set from PUPIL EPOCH, from https://github.com/pupil-labs/pupil/wiki/Data-Format#pupil-positions
                    # it is time since last boot, compute it here
                    # pupil tc in seconds 
                    self.pupil_epoch = system_tc - pt['timestamp']*1000 

                abs_tc = int(round(pt['timestamp']*1000 + self.pupil_epoch)) 
                self.last_gaze_tcs.append(pt['timestamp']) 
                
                if self.send_tc and not pt['timestamp'] in self.last_pupils_tcs:
                    #send tc
                    IvySendMsg("UB2;type=eyetracking:time;from={};ts={};device={}".format(self.app_name, abs_tc,  PupilUsybusController.device_id))
                    
                # get pupils size from base data used to compute gaze positions    
                base_data = pt['base_data']                  
                if len(base_data) == 0 or len(base_data) > 2:
                    # TODO - check if it is it possible? 
                    assert(False)
                else :
                    # in all cases timestamp has been added previously
                    assert(base_data[0]['timestamp'] in self.last_gaze_tcs)
                    if len(base_data) == 2 :
                        # TODO is it possible to have different timestamp? 
                        assert(base_data[0]['timestamp'] == base_data[1]['timestamp'])
                            
                    left_pup_diam = 'na' 
                    right_pup_diam = 'na' 
                    
                    # TODO remove this check, used to check data as some info are missing in doc
                    assert len(base_data) == 1, 'it is possible to have several elements in base_data!' 
                    for pupil in base_data : 
                        if pupil['id'] == 0 :
                            gaze_pupils[0] = True
                            left_pup_diam = pupil['diameter']
                        elif pupil['id'] == 1 :
                            gaze_pupils[1] = True
                            right_pup_diam = pupil['diameter']
                            
                    if self.send_gaze :
                        # handle data depending on player confidence :
                        confidence = 1
                        if pt['confidence'] < self.confidence :
                            confidence = 0
                        #send eyes gaze TODO add optional pupil fixation
                        IvySendMsg("UB2;type=eyetracking:gaze;from={};tc={};device={};xl={};yl={};xr={};yr={};pl={};pr={};vl={};vr={}".format(
                            self.app_name, 
                            int(abs_tc), 
                            PupilUsybusController.device_id,  
                            floatToString(pt['norm_pos'][0]),
                            floatToString(pt['norm_pos'][1]),
                            floatToString(pt['norm_pos'][0]),
                            floatToString(pt['norm_pos'][1]),
                            left_pup_diam, 
                            right_pup_diam,
                            confidence,
                            confidence
                        ))
                    
                self.pupil_display_list.append((pt['norm_pos'] , pt['confidence'], gaze_pupils))
            
        # TODO 
        # check if some additional pupil sizes are in pupil_positions
        # is it needed?  

        self.pupil_display_list[:-3] = []
   
   
    def update(self,frame,events):
        # same plugin used for capture and player 
        if self.g_pool.app == 'capture' :
            self.capture_update(frame,events)
        elif self.g_pool.app == 'player' :
            self.player_update(frame,events)
        else :
            assert False, 'plugin must run in pupil player or capture not in {}'.format(self.g_pool.app)


    def gl_display(self):
        for pt,a,gaze_pup in self.pupil_display_list:
            #This could be faster if there would be a method to also add multiple colors per point
            color=None 
            if gaze_pup[0] and gaze_pup[1] :
                color=RGBA(0, 1., 0, a)
            elif gaze_pup[0] and not gaze_pup[1] :
                color=RGBA(1., 1., 0, a)
            elif not gaze_pup[0] and gaze_pup[1] :
                color=RGBA(1., 1., 1., a)
            else: 
                color=RGBA(1., 0, 0, a)
                
            draw_points_norm([pt],
                        size=35,
                        color=color)


    def get_init_dict(self):
        return {}
    

    def cleanup(self):
        IvyStop()


    @staticmethod
    def set_device_id(device_id):   
        PupilUsybusController.device_id = device_id
				

    @staticmethod
    def on_ivy_conn(agent, connected):
        if connected == IvyApplicationDisconnected:
            print('Ivy application {} was disconnected'.format(agent))
        else:
            print('Ivy application {} was connected'.format(agent))
        print('currents Ivy application are [{}]'.format(IvyGetApplicationList()))


    @staticmethod
    def on_ivy_die(agent, _id):
        print('received the order to die from {} with id = {}'.format(agent, _id))
        
        
'''
Useful methods
'''
def floatToString(inputValue):
    return ('%.17f' % inputValue).rstrip('0').rstrip('.')
