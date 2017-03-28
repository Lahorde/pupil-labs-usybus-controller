from plugin import Plugin
from pyglui.cygl.utils import draw_points_norm,RGBA
from pyglui import ui
from ivy.std_api import *
import socket
import configparser
import datetime
import ivy
import logging
import collections

'''
Interface with pupillabs eye tracker. 
Pupilabs events -> published on Usybus
For info about pupillabs plugins 
http://docs.pupil-labs.com/#plugins-basics
'''
class PupilUsybusController(Plugin):
    device_id = 'pupil_usybus_controller'   	
    
    # keep last TIMESTAMP_CACHE_LENGTH timestamps, means that gaze at this timestamp has been handled
    TIMESTAMP_CACHE_LENGTH=10000
    # this cache is used in player 
    
    def __init__(self, g_pool):
        super(PupilUsybusController, self).__init__(g_pool)
        self.order = .8
        self.pupil_display_list = []
        # dict of surface_name keys with collections of  TIMESTAMP_CACHE_LENGTH timestamp value
        self.gaze_tcs = {} 
        # add default surface element
        self.gaze_tcs[PupilUsybusController.device_id] = collections.deque(maxlen=PupilUsybusController.TIMESTAMP_CACHE_LENGTH)
        
        self.send_tc = False 
        self.send_gaze = True 
        self.out_of_srf_gaze = False 
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

        # Disable info logs. Using logging library raises some exceptions. As 
        # a workaround, disable it
        logging.getLogger('Ivy').setLevel(logging.ERROR)
        
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
        self.menu.append(ui.Switch('out_of_srf_gaze',self,label='Out of surface gaze')) 
        self.menu.append(ui.Text_Input('device_id',self,setter=PupilUsybusController.set_device_id))
        self.menu.append(ui.Slider('confidence',self,min=0.1,step=0.01,max=1.0,label='Confidence')) 


    def start_tracking(self):
        pass
    
    
    def reset(self):
        # TODO check if synchro mechanisms needed
        for srf_timestamp_cache in self.gaze_tcs :
            self.gaze_tcs[srf_timestamp_cache].clear()

    def reset_tracking(self):
        pass


    def unset_alive(self):
        self.alive = False

    def capture_update(self,events):  
       self.publish_gaze(events, self.g_pool.eyes_are_alive[0].value, self.g_pool.eyes_are_alive[0].value)   
       
    def player_update(self,events):
       self.publish_gaze(events, True, True)   
       
    '''
    Only publish gaze_data associated with a surface
    '''
    def publish_gaze(self,events, left_eye, right_eye):
        # Refer here for data format http://docs.pupil-labs.com/#pupil-data-format 
        
        # when iterating over surfaces, add gaze not in defined surfaces, at end, publish
        # these gaze
        out_of_srf_cache=[] 
        for surface_index,pt in enumerate(events.get('surface',[])):
            # add timestamp cache for this surface
            if pt['name'] not in self.gaze_tcs :
                self.gaze_tcs[pt['name']] = collections.deque(maxlen=PupilUsybusController.TIMESTAMP_CACHE_LENGTH)
                
            if self.pupil_epoch is None :
                system_tc = (datetime.datetime.now() - datetime.datetime(1970, 1, 1, 0, 0)).total_seconds()*1000
                # pupil timestamps are set from PUPIL EPOCH, from https://github.com/pupil-labs/pupil/wiki/Data-Format#pupil-positions
                # it is time since last boot, compute it here
                # pupil tc in seconds 
                self.pupil_epoch = system_tc - pt['timestamp']*1000 
                
            for gaze_index,srf_gaze in enumerate(pt['gaze_on_srf']):
                abs_tc = int(round(srf_gaze['base_data']['timestamp']*1000 + self.pupil_epoch)) 
                
                if abs_tc in self.gaze_tcs[pt['name']] :
                    # this gaze has already been handled 
                    break
                
                self.gaze_tcs[pt['name']].append(abs_tc)
                
                if self.send_gaze :
                    # handle data depending on player confidence :
                    confidence = 'true' 
                    if srf_gaze['confidence'] < self.confidence :
                        confidence = 'false'
                        
                    optional_data='' 
                    # get right / left eyes optional data
                    # monocular or binocular eye tracking 
                    assert(len(srf_gaze['base_data']['base_data']) == 1 or  len(srf_gaze['base_data']['base_data']) == 2)  
                    for eye_data in srf_gaze['base_data']['base_data'] :
                        if eye_data['id'] == 0 :
                            eye = 'left'
                        elif eye_data['id'] == 1 :
                            eye = 'right'
                        else :
                            assert(False)

                        pupil_confidence = 'true' 
                        if eye_data['confidence'] < self.confidence :
                            pupil_confidence = 'false'
                        optional_data=';x-{0}={1};y-{0}={2};pupil-{0}={3};valid-{0}={4}'.format(
                            eye, 
                            floatToString(eye_data['norm_pos'][0]),
                            floatToString(eye_data['norm_pos'][1]),
                            floatToString(eye_data['diameter']),
                            pupil_confidence 
                        )
                            
                    if srf_gaze['on_srf'] == True:
                        # remove here gaze with on surface 
                        if gaze_index in out_of_srf_cache : 
                            out_of_srf_cache.remove(gaze_index)  
                       
                        ivy_msg= "UB2;type=eyetracking:gaze;from={};tc={};device={};surface={};x={};y={};valid={};inside={}{}".format(
                            self.app_name, 
                            int(abs_tc), 
                            PupilUsybusController.device_id,  
                            pt['name'], 
                            floatToString(srf_gaze['norm_pos'][0]),
                            floatToString(srf_gaze['norm_pos'][1]),
                            confidence, 
                            'true', 
                            optional_data,
                        )
                        IvySendMsg(ivy_msg)
                
                    elif self.out_of_srf_gaze :
                        if surface_index == 0:
                            #add all gaze out of srf 
                           out_of_srf_cache.append(gaze_index)  
                           
                        if surface_index ==  len(events.get('surface',[])) - 1 :
                            if gaze_index in out_of_srf_cache :  
                                ivy_msg= "UB2;type=eyetracking:gaze;from={};tc={};device={};surface={};x={};y={};valid={};inside={}{}".format(
                                    self.app_name, 
                                    int(abs_tc), 
                                    PupilUsybusController.device_id,  
                                    PupilUsybusController.device_id,  
                                    floatToString(srf_gaze['norm_pos'][0]),
                                    floatToString(srf_gaze['norm_pos'][1]),
                                    confidence, 
                                    'false', 
                                    optional_data,
                                )
                                IvySendMsg(ivy_msg)
                            
                else:
                    pass
                    
        # Display recent gazes                
        for pt in events.get('gaze_positions',[]): 
            # Is left pupil ? Is Right pupil? 
            gaze_pupils = [False, False]

            base_data = pt['base_data']                  
            # it is possible to have several elements in base_data! 
            for pupil in base_data : 
                if pupil['id'] == 0 :
                    gaze_pupils[0] = True
                    left_pup_diam = pupil['diameter']
                elif pupil['id'] == 1 :
                    gaze_pupils[1] = True
            self.pupil_display_list.append((pt['norm_pos'] , pt['confidence'], gaze_pupils))
            
        self.pupil_display_list[:-3] = []
   
   
    def recent_events(self,events):
        # same plugin used for capture and player 
        if self.g_pool.app == 'capture' :
            self.capture_update(events)
        elif self.g_pool.app == 'player' :
            self.player_update(events)
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
        # Workaround to restart later ivy server, if not reset to None, ivy will 
        # raise an assertion fail on next plugin restart
        ivy.std_api._IvyServer = None 
        self.reset() 
        if self.menu:
            self.g_pool.gui.remove(self.menu)
            self.menu = None


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
