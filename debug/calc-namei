#!/usr/bin/perl -w

use strict;

our @forward = qw( + = 0 1 2 3 4 5 6 7 8 9 A B C D E F G H I J K L M N O P Q R S T
                   U V W X Y Z a b c d e f g h i j k l m n o p q r s t u v w x y z );

our %reverse;
for (my $i = 0; $i < scalar @forward; $i++) {
        $reverse{ $forward[$i] } = $i;
}

foreach my $arg (@ARGV) {
    if ( $arg =~ /^\d+$/ ) {

	# my $volid = get_rw_volid( $arg );
	my $volid = $arg;			 # $arg has to be the ID of a RW volume

	my $path = "/vicep?/AFSIDat/" . num_to_char($volid & 0xff) . "/" . num_to_char($volid);

	printf "%9d:    %s\n", $volid, $path;

    } elsif ($arg =~ m|(/vicep.)?(/AFSIDat/)?([^/]+)/([^/]+)|) {

	my ($dir1, $dir2) = ($3, $4);

	my $path = "/vicep?/AFSIDat/$dir1/$dir2";
	my $volid = char_to_num($dir2);

	printf "%9d:    %s\n", $volid, $path;
    }
}

sub char_to_num {
    my $dir = shift;
    my $result;

    my $shift = 0;
    foreach my $char (split //, $dir) {

	my $n = $reverse{ $char };

	$n <<= $shift;
	$shift += 6;

	$result |= $n;
    }

    return $result;
}

sub num_to_char {

    my $number = shift;
    my $string;

    unless ( $number ) {
        $string = $forward[0];
    } else {

        my @string;

        my $index = 0;
        while ($number) {
            $string[$index] = $forward[ $number & 0x3f ];
            $index++;
            $number >>= 6;
        }

        $string = join "", @string;
    }
    return $string;
}
