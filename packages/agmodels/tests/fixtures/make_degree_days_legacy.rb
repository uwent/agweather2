# Rebuilds degree_days_legacy.csv from the old API's calculator (../ag-weather), for the parity test.
#   ruby packages/agmodels/tests/fixtures/make_degree_days_legacy.rb
# Every legacy pair (°F) and method over min/max pairs that straddle the thresholds.
require_relative "../../../../../ag-weather/app/models/degree_days_calculator"

PAIRS = [[32, nil], [38, 75], [39.2, 86], [41, nil], [41, 86], [42.8, 86], [45, nil], [45, 80.1], [45, 86],
  [48, nil], [50, nil], [50, 86], [50, 87.8], [50, 90], [52, nil], [52, 86], [55, 92]]
TEMPS = [-10, 20, 32, 36.5, 39.2, 41, 44, 48, 50, 52, 55, 60, 67.3, 75, 80.1, 84, 86, 88, 92, 100, 110]

out = File.join(__dir__, "degree_days_legacy.csv")
File.open(out, "w") do |f|
  f.puts "method,base,upper,min,max,dd"
  DegreeDaysCalculator::METHODS.each do |method|
    PAIRS.each do |base, upper|
      TEMPS.each do |min|
        TEMPS.each do |max|
          next if min > max
          dd = DegreeDaysCalculator.calculate(min:, max:, base:, upper:, method:)
          f.puts [method, base, upper, min, max, dd.round(6)].join(",")
        end
      end
    end
  end
end
puts "wrote #{out}"
