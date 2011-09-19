///////////////////////////////////////////////////////////////////////////////
//  Filename: $RCSfile: title2data.cpp,v $
//  Purpose:  Externl program example.
//  Language: Java
//  Compiler: GCC
//  Authors:  Joerg K. Wegner
//  Version:  $Revision: 1.1.1.1 $
//            $Date: 2004/12/06 15:33:04 $
//            $Author: wegner $
//
//  Copyright (c) Dept. Computer Architecture, University of Tuebingen, Germany
//
//  This program is free software; you can redistribute it and/or modify
//  it under the terms of the GNU General Public License as published by
//  the Free Software Foundation version 2 of the License.
//
//  This program is distributed in the hope that it will be useful,
//  but WITHOUT ANY WARRANTY; without even the implied warranty of
//  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
//  GNU General Public License for more details.
///////////////////////////////////////////////////////////////////////////////

#include <iostream>
#include <fstream>
#include <stdio.h>

using namespace std;

int main(int argc,char **argv)
{
	char *buffer = new char[10000];
	char *title = new char[1000];
	int i,n;
	char ch;
	int line=1;
	int end;
	char *attribute = "MOL_TITLE";

	if(argc>1)attribute=argv[1];
	cout<<"CPP: start"<<endl;
	for(;;)
	{
	   end=0;
	   for( i = 0; ((ch = getchar()) != EOF) && (ch != '\n'); i++ )
	   {
		  buffer[i] = (char)ch;
		  if(i<4)
		  {
		  	end|=(end<<1);
			if(ch=='$')end|=1;
		  }
	   }
	   
	   if(end!=15)
	   {
	     buffer[i] = '\0';
	     printf( "line %i:%s\n\r",line, buffer );
	     printf( "%s\n\r", buffer );
	   }
	   if(line==1)
	   {
	   	for( n = 0; n<=i; n++ )
		{
			title[n]=buffer[n];
	   	}
	   }

	   if(ch==EOF || end==15)
	   {
 		break;
	   }

	   line++;
	}
	
	//write simple data entry
	printf( ">  <%s>\n\r",attribute);
	printf( "%s\n\r", title );
	printf( "\n\r$$$$" );
	//cout << "fini"<<endl;
	return 0;
}
