# axon_finding_right_x - from axon
# axon_finding_left_x  - from axon
# frame_width - from as provided to axon
# boat_heading - as recived from msg 4200 (from VMS)
# cam_fov - From configuration file (default value 90)
# camera_shift - From configuration file (default value 0)
def calc_corrected_heading(frame_width, boat_heading, axon_finding_left_x, axon_finding_right_x, camera_shift=0, camera_fov=90):
    try:
        frame_width = float(frame_width)
    except:
        pass
    try:
        boat_heading = float(boat_heading)
    except:
        pass
    try:
        axon_finding_left_x = int(axon_finding_left_x)
    except:
        pass
    try:
        axon_finding_right_x = int(axon_finding_right_x)
    except:
        pass
    try:
        if frame_width <= 0 or boat_heading < -180 or boat_heading > 180:
            return None
        if axon_finding_left_x > frame_width or axon_finding_left_x < 0:
            return None
        if axon_finding_right_x > frame_width or axon_finding_right_x < 0:
            return None
        if axon_finding_left_x > axon_finding_right_x:
            tmp = axon_finding_right_x
            axon_finding_right_x = axon_finding_left_x
            axon_finding_left_x = tmp

        # Heading value correction to 360 from +-180 degrees
        normalized_heading = (360 + boat_heading) % 360

        # Calculate axon finding center
        axon_finding = (axon_finding_right_x - axon_finding_left_x) / 2 + axon_finding_left_x

        # Calculate ammount of degrees to shift from the heading
        shift_deg = abs(frame_width / 2 - axon_finding) * (camera_fov / frame_width)

        if axon_finding < frame_width / 2:
            corrected_heading = normalized_heading - shift_deg
        else:
            corrected_heading = normalized_heading + shift_deg

        # left center and right camera shifts degrees are according to the true boat heading

        corrected_heading = (corrected_heading + camera_shift) % 360
        # print(f"@@@@@@@@@@@@@@@@ corrected_heading = {corrected_heading}")
        return corrected_heading
    except BaseException as e:
        print("[ERROR] calc_corrected_heading: ", e)
    return None
