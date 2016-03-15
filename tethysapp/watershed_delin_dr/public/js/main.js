var map, click_point_layer, river_layer, basin_layer;
var outlet_x, outlet_y;

var displayStatus = $('#display-status');


$(document).ready(function () {

    map = new ol.Map({
	layers: [ ],
	controls: ol.control.defaults(),
	target: 'map',
	view: new ol.View({
		zoom: 8,
        projection: "EPSG:3857"
	})
    });

    bing_layer = new ol.layer.Tile({
		source: new ol.source.BingMaps({
			imagerySet: 'AerialWithLabels',
			key: 'SFpNe1Al6IDxInoiI7Ta~LX-BVFN0fbUpmO4hIUm3ZA~AsJ3XqhA_0XVG1SUun4_ibqrBVYJ1XaYJdYUuHGqVCPOM71cx-3FS2FzCJCa2vIh'
		})
	});

    river_layer = new ol.layer.Vector({
        source: new ol.source.Vector({
          url: "/static/watershed_delin_dr/kml/dr_stream_lines_1k.kml",
          format: new ol.format.KML(),
         })
      });

    click_point_layer = new ol.layer.Vector({
      source: new ol.source.Vector(),
      style: new ol.style.Style({
        fill: new ol.style.Fill({
          color: 'rgba(255, 255, 255, 0.2)'
        }),
        stroke: new ol.style.Stroke({
          color: '#ffcc33',
          width: 2
        }),
        image: new ol.style.Circle({
          radius: 7,
          fill: new ol.style.Fill({
            color: '#ffcc33'
          })
        })
      })
    });

    basin_layer = new ol.layer.Vector({
    source: new ol.source.Vector({
        features: new ol.format.GeoJSON()
    }),
    style: new ol.style.Style({
        stroke: new ol.style.Stroke({
        color: 'blue',
        lineDash: [4],
        width: 3
        }),
        fill: new ol.style.Fill({
        color: 'rgba(0, 0, 255, 0.1)'
        })
    })
    });

    map.addLayer(bing_layer);

    map.addLayer(click_point_layer);
    map.addLayer(river_layer);
    map.addLayer(basin_layer);

    var lat = 18.9108;
    var lon = -71.2500;
    CenterMap(lat, lon);
    map.getView().setZoom(8);

    map.on('click', function(evt) {
        var coordinate = evt.coordinate;
        addClickPoint(evt.coordinate);

        //Proj4js.defs["EPSG:3395"]='+title=world mercator EPSG:3395 +proj=merc +lon_0=0 +k=1 +x_0=0 +y_0=0 +ellps=WGS84 +datum=WGS84 +units=m +no_defs';
        //var source = new Proj4js.Proj("EPSG:3857");
        //var dest = new Proj4js.Proj("EPSG:3395");
        //
        //var p = new Proj4js.Point(evt.coordinate[0],evt.coordinate[1]);   //any object will do as long as it has 'x' and 'y' properties
        //var new_xy_3395 = Proj4js.transform(source, dest, p);      //do the transformation.  x and y are modified in place


        outlet_x = coordinate[0];
        outlet_y = coordinate[1];
        map.getView().setCenter(evt.coordinate);
        map.getView().setZoom(15);

    })

});

function CenterMap(lat,lon){
    var dbPoint = {
        "type": "Point",
        "coordinates": [lon, lat]
    }
    var coords = ol.proj.transform(dbPoint.coordinates, 'EPSG:4326','EPSG:3857');
    map.getView().setCenter(coords);
}

function addClickPoint(coordinates){
    // Check if the feature exists. If not then create it.
    // If it does exist, then just change its geometry to the new coords.
    var geometry = new ol.geom.Point(coordinates);
    if (click_point_layer.getSource().getFeatures().length==0){
        var feature = new ol.Feature({
            geometry: geometry,
            attr: 'Some Property'
        });
        click_point_layer.getSource().addFeature(feature);
    } else {
        click_point_layer.getSource().getFeatures()[0].setGeometry(geometry);
    }
}

function geojson2feature(myGeoJSON) {
    //Convert GeoJSON object into an OpenLayers 3 feature.
    var geojsonformatter = new ol.format.GeoJSON();
    var myFeature = geojsonformatter.readFeatures(myGeoJSON);
    //var myFeature = new ol.Feature(myGeometry);
    return myFeature;

}

function run_sc_service() {

    alert(outlet_x);
    alert(outlet_y);

    basin_layer.getSource().clear();

    displayStatus.removeClass('error');
    displayStatus.addClass('calculating');
    displayStatus.html('<em>Calculating...</em>');

    $.ajax({
        type: 'GET',
        url: 'run',
        dataType:'json',
        data: {
                'xlon': outlet_x,
                'ylat': outlet_y,
                'prj' : "native"
        },
        success: function (data) {

            basin_layer.getSource().addFeatures(geojson2feature(data));
            displayStatus.removeClass('calculating');
            displayStatus.addClass('success');
            displayStatus.html('<em>Success!</em>');

        },
        error: function (jqXHR, textStatus, errorThrown) {
            alert("Error");
            displayStatus.removeClass('calculating');
            displayStatus.addClass('error');
            displayStatus.html('<em>' + errorThrown + '</em>');
        }
    });

}
