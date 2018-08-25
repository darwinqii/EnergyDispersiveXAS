from near_edge_imaging import *
import numpy as np
from beam_near_edge_imaging import beam_near_edge_imaging
from nei_beam_parameters import nei_beam_parameters


def nei(materials='', path='', n_proj=900,
        slice=0, multislice=False, ct=False, side_width=0,
        display=True, pop_up_image=False, setup_type='FILE',
        order_files=False, e_range=0,lowpass=False,
        fix_vertical_motion=False,  # maybe change default to True
        clip=False, flip=False, fix_cross_over=False,width_factor=1.0,
        use_sm_data=False, use_measured_standard=False,
        use_weights=False, energy_weights=0, flat_gamma=1.0,
        put_dark_back=False, fix_detector_factor=0,
        Verbose=False):
    """
    Get beam_parameters, then do the beam_near_edge_imaging. Get $\mu t$ for all
    projection images.
    :param materials:
    :param path:
    :param left:
    :param right:
    :param n_proj:
    :param slice:
    :param multislice:
    :param projection:
    :param e_range:
    :param fix_vertical_motion:
    :param fix_cross_over:
    :param flat_gamma:
    :param Verbose:
    :return:
    """

    ###############   define materials       ######################
    if materials == '':
        names = ['K2SeO4', 'K2SeO3', 'Se-Meth', 'Water']
        sources = ['FILE', 'FILE', 'FILE', 'SYSTEM']
        materials = {}
        for i in range(len(names)):
            materials[names[i]] = sources[i]

    ##############   get path for experiment data file  ################
    if path == '':
        path = choose_path()
    print("Data directory: ",path)

    #############  get system setup info from arrangement.dat   ##########
    setup = nei_get_arrangement(setup_type, path)
    detector = setup.detector
    # redefine energy_range if needed
    if e_range != 0: setup.energy_range = e_range

    ########  get beam files: averaged flat, dark, and edge  ############
    print('\n(nei) Running "get_beam_files"')
    beam_files = get_beam_files(path=path, clip=clip, flip=flip, Verbose=Verbose)

    #####################  get tomo data  ########################
    print('(nei) Running "get_tomo_files"')
    tomo_data = get_tomo_files(path,multislice=False,slice=1,n_proj=n_proj)

    #################### Get beam_parameters #####################
    print('\n(nei) Running "nei_beam_parameters"\n')

    beam_parameters = nei_beam_parameters(display=display, beam_files=beam_files,
                                              setup=setup, detector=detector,
                                              fix_vertical_motion=fix_vertical_motion,
                                              clip=clip,Verbose=Verbose)

    ####################  Main calculation  #################################
    '''
    The following is the main calculation for Energy Dispersive Xray Absorption Spectroscopy.
    
    - We get get mu_rho values for every material at every y,x position on the detector (in the image).
    - We calculate the $\mu t$ for every y position (representing energy) at every x position
        (representing horizontal position in the sample, in every tomo image.
    - We calculate the $\rho t$ at every horizontal position for every material.
    In theory, if there is only one material, we can solve the $\rho t$ with the information at one energy
    position, by $(\mu t)/(\mu/\rho)$. When we have 3 materials, we can solve it with 3 energy points.
    In reality, we have sometimes about 900 energy points, so we use linear regression (or other algorithm)
    to solve the coefficient of every material.
    '''
    ##########  get murho values for every material at [y,x] position  ############
    print('\n(nei) Running "nei_determine_murhos"')
    gaussian_energy_width = beam_parameters.e_width * width_factor  # gaussian edge width in terms of energy
    exy = beam_parameters.exy
    mu_rhos = nei_determine_murhos(materials, exy, gaussian_energy_width=gaussian_energy_width,
                                    use_measured_standard=use_measured_standard)

    ####################  calculate -ln(r)=  mu/rho * rho * t   #################
    print('\n(nei) Running "calculate_mut"')
    mu_t = calculate_mut(tomo_data, beam_parameters, lowpass=lowpass,
                         ct=ct, side_width=side_width)

    ####################  Todo: something to reduce artifact   ############

    ####################          calculate rho*t               #################
    beam = beam_parameters.beam
    print('\n(nei) Running "calculate_rhot"')
    rts = calculate_rhot(mu_rhos, mu_t, beam)

    class Result:
        def __init__(self, beam_parameters, mu_rhos, mu_t,rts):
            self.beam_parameters = beam_parameters
            self.mu_rhos = mu_rhos
            self.mu_t = mu_t
            self.rts = rts

    return Result(beam_parameters, mu_rhos, mu_t,rts)