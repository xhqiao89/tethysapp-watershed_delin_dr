from tethys_sdk.base import TethysAppBase, url_map_maker


class DrWatershedDelineation(TethysAppBase):
    """
    Tethys app class for DR Watershed Delineation.
    """

    name = 'Watershed Delineation DR'
    index = 'watershed_delin_dr:home'
    icon = 'watershed_delin_dr/images/icon.gif'
    package = 'watershed_delin_dr'
    root_url = 'watershed-delin-dr'
    color = '#3399ff'
    description = 'Place a brief description of your app here.'
    enable_feedback = False
    feedback_emails = []


    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = (UrlMap(name='home',
                           url='watershed-delin-dr',
                           controller='watershed_delin_dr.controllers.home'),
                    UrlMap(name='run',
                           url='watershed-delin-dr/run',
                           controller='watershed_delin_dr.controllers.run_sc')
                    )

        return url_maps