# Dumps VDIFN's db/seeds.rb pest records (name, local_name, info, photo, link) as JSON, over stub models.
require "json"
$records = []
class Stub
  def initialize(attrs = {}) = (@attrs = attrs)
  def method_missing(name, *args, **kw) = self
  def respond_to_missing?(*) = true
end
class Object
  def self.const_missing(name)
    klass = Class.new do
      define_singleton_method(:create!) { |attrs = {}| $records << attrs.merge(type: name.to_s); Stub.new(attrs) }
      define_singleton_method(:method_missing) { |*a, **k| Stub.new }
      define_singleton_method(:respond_to_missing?) { |*| true }
    end
    const_set(name, klass)
  end
end
begin
  load ARGV[0]
rescue => e
  warn "stopped at #{e.class}: #{e.message}"
end
puts JSON.pretty_generate($records.select { |r| r[:local_name] }.map { |r| r.slice(:type, :name, :local_name, :info, :severity_info, :photo, :link) })
