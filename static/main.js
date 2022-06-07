(function () {

  'use strict';

  angular.module('ProspectApp', [])

  .controller('ProspectController', ['$scope', '$log', '$http', '$timeout',
    function($scope, $log, $http, $timeout) {

    $scope.refreshButtonText = 'Refresh';
    $scope.loading = false;
    $scope.urlerror = false;

    $scope.getResults = function() {

      $log.log('test');

      // get the URL from the input
      var userInput = $scope.url;

      // fire the API request
      $http.post('/refresh').
        success(function(results) {
          $log.log(results);
          getProspects(results);
          $scope.prospects = null;
          $scope.loading = true;
          $scope.refreshButtonText = 'Loading...';
          $scope.urlerror = false;
        }).
        error(function(error) {
          $log.log(error);
        });

    };

    function getProspects(jobID) {

      var timeout = '';

      var poller = function() {
        // fire another request
        $http.get('/results/'+jobID).
          success(function(data, status, headers, config) {
            if(status === 202) {
              $log.log(data, status);
            } else if (status === 200){
              $log.log(data);
              $scope.loading = false;
              $scope.refreshButtonText = "Refresh";
              $scope.prospects = data;
              $timeout.cancel(timeout);
              return false;
            }
            // continue to call the poller() function every 2 seconds
            // until the timeout is cancelled
            timeout = $timeout(poller, 2000);
          }).
          error(function(error) {
            $log.log(error);
            $scope.loading = false;
            $scope.refreshButtonText = "Refresh";
            $scope.urlerror = true;
          });
      };

      poller();

    }

  }])

  .directive('prospectChart', ['$parse', function ($parse) {
    return {
      restrict: 'E',
      replace: true,
      template: '<div id="chart"></div>',
      link: function (scope) {
        scope.$watch('prospects', function() {
          d3.select('#chart').selectAll('*').remove();
          var data = scope.prospects;
          for (var person in data) {
            var key = data[person][0];
            var value = data[person][1];
            d3.select('#chart')
              .append('div')
              .selectAll('div')
              .data(person)
              .enter()
              .append('div')
              .style('width', function() {
                return (value * 3) + 'px';
              })
              .text(function(d){
                return key;
              });
          }
        }, true);
      }
     };
  }]);

}());
