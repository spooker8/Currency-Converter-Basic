//
//  ViewController.h
//  Peer 3
//
//  Created by Anand Kumar on 9/19/15.
//  Copyright © 2015 Anand Kumar. All rights reserved.
//

#import <UIKit/UIKit.h>
#import "CurrencyRequest/CRCurrencyRequest.h"
#import "CurrencyRequest/CRCurrencyResults.h"

@interface ViewController : UIViewController


@property (nonatomic) CRCurrencyRequest *req;

@property (weak, nonatomic) IBOutlet UITextField *inputField;

@property (weak, nonatomic) IBOutlet UIButton *convertButton;


@property (weak, nonatomic) IBOutlet UISegmentedControl *segmentController;

@property (weak, nonatomic) IBOutlet UILabel *outputField;



@end

