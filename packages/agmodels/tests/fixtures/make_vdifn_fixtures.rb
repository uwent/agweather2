# Rebuilds vdifn_*.csv from VDIFN's insect severity code (../ag-vdifn), for the insect parity tests.
#   ruby packages/agmodels/tests/fixtures/make_vdifn_fixtures.rb
# Loads VDIFN's Insect and OakWilt classes over a stub of their ActiveRecord parent.
require "date"

class Pest
  attr_accessor :risk_array
end
vdifn = File.expand_path("../../../../../ag-vdifn/app/models", __dir__)
require File.join(vdifn, "insect")
require File.join(vdifn, "insects/oak_wilt")

ARRAYS = {
  "generations_1" => [[300, 504, 814]],
  "generations_2" => [[325, 520, 750], [1115, 1310, 1540]],
  "touching" => [[265, 895, 1115], [1115, 1375, 2500]],
  "generations_4" => [[340, 675, 1010], [1010, 1350, 1685], [1685, 2025, 2360], [2360, 2700, 3375]]
}

File.open(File.join(__dir__, "vdifn_insect_severity_sweep.csv"), "w") do |f|
  f.puts "array,dd,freezing,severity"
  ARRAYS.each do |name, array|
    insect = Insect.new
    insect.risk_array = array
    (0..3500).step(5).each do |dd|
      [0, 2].each do |freezing|
        f.puts [name, dd, freezing, insect.total_to_severity(dd.to_f, freezing: freezing)].join(",")
      end
    end
  end
end

File.open(File.join(__dir__, "vdifn_oak_wilt_sweep.csv"), "w") do |f|
  f.puts "dd,day_of_year,severity"
  oak = OakWilt.new
  (0..2500).step(10).each do |dd|
    [120, 180, 195, 196, 202, 203, 250].each do |yday|
      date = Date.new(2025, 1, 1) + (yday - 1)
      f.puts [dd, yday, oak.total_to_severity(dd.to_f, date: date, freezing: 0)].join(",")
    end
  end
end
puts "wrote vdifn_insect_severity_sweep.csv, vdifn_oak_wilt_sweep.csv"
